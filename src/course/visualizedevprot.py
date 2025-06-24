import os
import rasterio
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams
from pyproj import Transformer

class RasterVisualizer:
    def __init__(self, raster_dir, output_path):
        """
        初始化栅格可视化类
        :param raster_dir: 栅格文件夹路径
        :param output_path: 输出图片保存路径
        """
        self.raster_dir = raster_dir
        self.output_path = output_path

        # 定义栅格文件对应的土地类型名称
        self.land_type_names = [
            "农田", "森林", "荒地", "草原", "水域", "不透水面"
        ]

        # 设置中文字体支持
        rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
        rcParams['axes.unicode_minus'] = False   # 解决负号显示问题

    def _transform_extent_to_wgs84(self, extent, src_crs):
        """
        将栅格的范围从投影坐标系转换为经纬度坐标系
        :param extent: 栅格的范围 [left, right, bottom, top]
        :param src_crs: 栅格的原始坐标系
        :return: 转换后的范围 [min_lon, max_lon, min_lat, max_lat]
        """
        transformer = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
        min_lon, min_lat = transformer.transform(extent[0], extent[2])
        max_lon, max_lat = transformer.transform(extent[1], extent[3])
        return [min_lon, max_lon, min_lat, max_lat]

    def _plot_raster(self, raster_path, ax, title):
        """
        绘制单个栅格文件的热力图
        :param raster_path: 栅格文件路径
        :param ax: 子图对象
        :param title: 图标题
        """
        with rasterio.open(raster_path) as src:
            data = src.read(1)  # 读取第一波段数据
            extent = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]  # 获取坐标范围

            # 将范围转换为经纬度
            extent_wgs84 = self._transform_extent_to_wgs84(extent, src.crs)

            # 将 nodata 值替换为 NaN
            nodata = src.nodata
            if nodata is not None:
                data = np.where(data == nodata, np.nan, data)

            # 绘制热力图
            im = ax.imshow(data, cmap="YlGnBu", extent=extent_wgs84, origin="upper", vmin=0, vmax=255)
            ax.set_title(title, fontsize=14)  # 修改标题字体大小为 14px
            ax.tick_params(labelsize=14)  # 修改刻度字体大小为 14px
            ax.grid(False)

            # 设置坐标轴标签
            ax.set_xlabel("经度", fontsize=14)  # 修改 X 轴标签字体大小为 14px
            ax.set_ylabel("纬度", fontsize=14)  # 修改 Y 轴标签字体大小为 14px

            return im

    def visualize(self):
        """
        绘制栅格文件的热力图组
        """
        # 获取栅格文件列表
        raster_files = sorted([f for f in os.listdir(self.raster_dir) if f.endswith(".tif")])

        # 创建图形，调整行间距
        fig, axes = plt.subplots(
            2, 3, figsize=(16, 10), 
            constrained_layout=True,
            gridspec_kw={"hspace": 0}
        )
        axes = axes.flatten()

        # 绘制每个栅格文件
        for i, raster_file in enumerate(raster_files):
            raster_path = os.path.join(self.raster_dir, raster_file)
            self._plot_raster(raster_path, axes[i], self.land_type_names[i])

        # 添加统一图例到右侧
        norm = plt.Normalize(vmin=0, vmax=255)
        sm = plt.cm.ScalarMappable(cmap="YlGnBu", norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=axes, orientation="vertical", fraction=0.03, pad=0.05)
        cbar.set_label("栅格值", fontsize=14)  # 修改图例标签字体大小为 14px
        cbar.ax.tick_params(labelsize=14)  # 修改图例刻度字体大小为 14px

        # 保存图片
        plt.savefig(self.output_path, dpi=300)
        plt.show()

if __name__ == "__main__":
    raster_dir = r"F:\landuse\data\unsignedchar\homework\devprot2unif"
    output_path = r"F:\landuse\data\unsignedchar\homework\visualized_rasters.png"

    visualizer = RasterVisualizer(raster_dir, output_path)
    visualizer.visualize()