import asyncio
import numpy as np
import rasterio
from scipy.spatial import ConvexHull
from sklearn.cluster import DBSCAN
from rasterio.warp import transform as warp_transform
from scipy.ndimage import binary_opening

from ..core import config

class NDVICalculator:
    def __init__(self, logger):
        self.logger = logger
        self.scale_factor = config.NDVI_SCALE_FACTOR

    def _compute_sync(self, red_url: str, nir_url: str):
        """
        Синхронная функция для тяжелых вычислений (запускается в потоке).
        """
        env = rasterio.Env(
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            CPL_VSIL_CURL_ALLOWED_EXTENSIONS="tif",
            VSI_CACHE="TRUE"
        )

        with env:
            with rasterio.open(red_url) as src_red:
                red = src_red.read(1, out_shape=(1, int(src_red.height // self.scale_factor),
                                                 int(src_red.width // self.scale_factor)))
                transform = src_red.transform
                crs = src_red.crs

            with rasterio.open(nir_url) as src_nir:
                nir = src_nir.read(1, out_shape=(1, int(src_nir.height // self.scale_factor),
                                                 int(src_nir.width // self.scale_factor)))

        red = red.astype(np.float32)
        nir = nir.astype(np.float32)
        ndvi_matrix = (nir - red) / (nir + red + 1e-8)
        ndvi_matrix = np.clip(ndvi_matrix, -1, 1)

        dry_mask = (ndvi_matrix > 0.15) & (ndvi_matrix < 0.25)

        cleaned_mask = binary_opening(dry_mask, structure=np.ones((3, 3)))

        dry_rows, dry_cols = np.where(cleaned_mask)

        problem_areas = []
        cluster_centers_pixels = []  # Центры для графика
        cluster_polygons_pixels = []  # Оболочки (полигоны) для графика

        if len(dry_rows) > 0:
            points = np.column_stack((dry_rows, dry_cols))
            clustering = DBSCAN(eps=5, min_samples=10).fit(points)
            labels = clustering.labels_
            unique_labels = set(labels)

            for label in unique_labels:
                if label == -1:
                    continue

                cluster_points = points[labels == label]

                center_row = np.mean(cluster_points[:, 0])
                center_col = np.mean(cluster_points[:, 1])
                cluster_centers_pixels.append((center_col, center_row))


                try:
                    hull = ConvexHull(cluster_points)
                    hull_vertices = cluster_points[hull.vertices]
                except Exception:
                    hull_vertices = cluster_points

                poly_vertices_px = [(pt[1], pt[0]) for pt in hull_vertices]
                cluster_polygons_pixels.append(poly_vertices_px)

                center_x, center_y = rasterio.transform.xy(transform, center_row * self.scale_factor,
                                                           center_col * self.scale_factor)

                hull_rows = hull_vertices[:, 0] * self.scale_factor
                hull_cols = hull_vertices[:, 1] * self.scale_factor
                hull_xs, hull_ys = rasterio.transform.xy(transform, hull_rows, hull_cols)

                all_xs = [center_x] + list(hull_xs)
                all_ys = [center_y] + list(hull_ys)

                longitudes, latitudes = warp_transform(crs, 'EPSG:4326', all_xs, all_ys)

                true_lon, true_lat = longitudes[0], latitudes[0]

                polygon_geo_coords = [
                    {"lat": round(lat, 6), "lon": round(lon, 6)}
                    for lat, lon in zip(latitudes[1:], longitudes[1:])
                ]

                problem_areas.append({
                    "center_lat": round(true_lat, 6),
                    "center_lon": round(true_lon, 6),
                    "polygon": polygon_geo_coords,
                    "cluster_size_pixels": int(len(cluster_points))
                })

        dry_percentage = float(np.sum(cleaned_mask) / cleaned_mask.size)
        mean_ndvi = float(np.mean(ndvi_matrix))

        problem_areas = sorted(problem_areas, key=lambda x: x["cluster_size_pixels"], reverse=True)
        top_problem_areas = problem_areas[:50]

        return {
            "mean_ndvi": mean_ndvi,
            "dry_area_fraction": dry_percentage,
            "total_risk_zones": len(problem_areas),
            "problem_areas": top_problem_areas
        }

    async def get_mean_ndvi(self, red_url: str, nir_url: str):
        """
        Асинхронная обертка для запуска тяжелой математики в отдельном потоке.
        """
        self.logger.info("Запуск расчета NDVI в фоновом потоке...")
        try:
            result = await asyncio.to_thread(self._compute_sync, red_url, nir_url)
            self.logger.info("Расчет NDVI завершен", extra={"extra_data": result})
            return result
        except Exception as e:
            self.logger.error("Ошибка при расчете NDVI матриц", exc_info=True)
            return None