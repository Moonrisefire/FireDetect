import asyncio
import numpy as np
import rasterio
from scipy.spatial import ConvexHull
from sklearn.cluster import DBSCAN
from rasterio.warp import transform as warp_transform
from rasterio.warp import transform_bounds
from rasterio.windows import Window, from_bounds
from scipy.ndimage import binary_opening

from ..core import config

# Полоса 0.15–0.25 — определение сухости из обучения. Признаки модели считаются по всему гранулу.
NDVI_DRY_MIN = 0.15
NDVI_DRY_MAX = 0.25


def empty_ndvi() -> dict:
    return {
        "mean_ndvi": 0.0,
        "dry_area_fraction": 0.0,
        "total_risk_zones": 0,
        "problem_areas": [],
    }

class NDVICalculator:
    def __init__(self, logger):
        self.logger = logger
        self.scale_factor = config.NDVI_SCALE_FACTOR

    def _window_index_bounds(self, transform, crs, height: int, width: int, lat: float, lon: float):
        """Границы окна клика в индексах уменьшенного растра. None — окно посчитать нельзя."""
        if crs is None:
            return None
        buffer_deg = config.AOI_BUFFER_DEG
        left, bottom, right, top = transform_bounds(
            "EPSG:4326",
            crs,
            lon - buffer_deg,
            lat - buffer_deg,
            lon + buffer_deg,
            lat + buffer_deg,
            densify_pts=21,
        )
        window = from_bounds(left, bottom, right, top, transform=transform)
        window = window.intersection(Window(0, 0, width, height))
        if window.width <= 0 or window.height <= 0:
            return (0.0, 0.0, 0.0, 0.0)
        scale = self.scale_factor
        return (
            window.row_off / scale,
            (window.row_off + window.height) / scale,
            window.col_off / scale,
            (window.col_off + window.width) / scale,
        )

    def _compute_sync(self, red_url: str, nir_url: str, lat: float, lon: float):
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
                raster_height = src_red.height
                raster_width = src_red.width
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

        dry_mask = (ndvi_matrix > NDVI_DRY_MIN) & (ndvi_matrix < NDVI_DRY_MAX)

        cleaned_mask = binary_opening(dry_mask, structure=np.ones((3, 3)))

        dry_rows, dry_cols = np.where(cleaned_mask)
        # mean_ndvi и dry_area_fraction остаются по всему снимку.
        # DBSCAN ниже — только пиксели внутри окна вокруг клика, для карты.
        bounds = self._window_index_bounds(transform, crs, raster_height, raster_width, lat, lon)
        if bounds is None:
            dry_rows = dry_rows[:0]
            dry_cols = dry_cols[:0]
        else:
            row0, row1, col0, col1 = bounds
            keep = (dry_rows >= row0) & (dry_rows < row1) & (dry_cols >= col0) & (dry_cols < col1)
            dry_rows = dry_rows[keep]
            dry_cols = dry_cols[keep]

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

    async def get_mean_ndvi(self, red_url: str, nir_url: str, lat: float, lon: float):
        """
        Асинхронная обертка для запуска тяжелой математики в отдельном потоке.
        """
        self.logger.info("Запуск расчета NDVI в фоновом потоке...")
        try:
            result = await asyncio.to_thread(self._compute_sync, red_url, nir_url, lat, lon)
            self.logger.info("Расчет NDVI завершен", extra={"extra_data": result})
            return result
        except Exception as e:
            self.logger.error("Ошибка при расчете NDVI матриц", exc_info=True)
            return None