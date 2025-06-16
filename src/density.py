import os
import geopandas as gpd
import rasterio
from rasterio.transform import from_origin
import numpy as np
from tqdm import tqdm

class PointDensityRasterizer:
    def __init__(self, poi_shp_path, foshan_shp_path, output_dir, resolution=30):
        self.poi_shp_path = poi_shp_path
        self.foshan_shp_path = foshan_shp_path
        self.output_dir = output_dir
        self.resolution = resolution

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"输出目录 {self.output_dir} 已创建。")

    def reproject_shp(self, input_shp_path, target_crs):
        gdf = gpd.read_file(input_shp_path)
        gdf = gdf.to_crs(epsg=target_crs)
        return gdf

    def calculate_raster_dimensions(self, foshan_gdf):
        bounds = foshan_gdf.total_bounds
        minx, miny, maxx, maxy = bounds
        width = int((maxx - minx) / self.resolution)
        height = int((maxy - miny) / self.resolution)

        if width <= 0 or height <= 0:
            return None, None, None

        transform = from_origin(minx, maxy, self.resolution, self.resolution)
        return width, height, transform

    def create_combined_raster(self, poi_gdf_32649, foshan_gdf_32649, foshan_gdf_4326):
        width, height, transform_32649 = self.calculate_raster_dimensions(foshan_gdf_32649)
        if width is None or height is None or transform_32649 is None:
            print("警告: 投影坐标系栅格宽度或高度为零，跳过处理。")
            return

        raster_32649 = np.zeros((height, width), dtype=np.float32)
        for _, point in tqdm(poi_gdf_32649.iterrows(), desc="计算点密度 (EPSG:32649)"):
            px, py = point.geometry.x, point.geometry.y
            col = int((px - transform_32649[2]) / self.resolution)
            row = int((transform_32649[5] - py) / self.resolution)
            if 0 <= col < width and 0 <= row < height:
                raster_32649[row, col] += 1

        # 保存栅格文件，主坐标系为 EPSG:32649
        output_path = os.path.join(self.output_dir, "density_poi.tif")
        with rasterio.open(
            output_path,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype=raster_32649.dtype,
            crs=foshan_gdf_32649.crs.to_string(),
            transform=transform_32649,
        ) as dst:
            dst.write(raster_32649, 1)

            # 添加地理坐标系的元数据
            transform_4326 = from_origin(
                foshan_gdf_4326.total_bounds[0],
                foshan_gdf_4326.total_bounds[3],
                self.resolution / 111320.0,
                self.resolution / 111320.0,
            )
            dst.update_tags(ns="EPSG:4326", transform=str(transform_4326))
        print(f"栅格文件保存到: {output_path}")

    def process(self):
        foshan_gdf_32649 = self.reproject_shp(self.foshan_shp_path, target_crs=32649)
        poi_gdf_32649 = self.reproject_shp(self.poi_shp_path, target_crs=32649)
        foshan_gdf_4326 = self.reproject_shp(self.foshan_shp_path, target_crs=4326)
        self.create_combined_raster(poi_gdf_32649, foshan_gdf_32649, foshan_gdf_4326)


def test_point_density_rasterizer():
    poi_shp_path = "F:/landuse/data/poi/foshanpoi.shp"
    foshan_shp_path = "F:/landuse/data/foshan/foshan.shp"
    output_dir = "F:/landuse/data/density"
    rasterizer = PointDensityRasterizer(poi_shp_path, foshan_shp_path, output_dir)
    rasterizer.process()


if __name__ == "__main__":
    test_point_density_rasterizer()