import os
import rasterio
import matplotlib.pyplot as plt
from matplotlib import rcParams
import numpy as np
import geopandas as gpd
import matplotlib.patches as mpatches
from rasterio.features import geometry_mask 
import pyproj

class LandUseVisualizer:
    def __init__(self, pred_dir, true_dir, relativee_path, shapefile_path, output_path):
        """
        初始化土地利用可视化类
        :param pred_dir: 预测值文件夹路径
        :param true_dir: 真实值文件夹路径
        :param relativee_path: 相对误差文件路径
        :param shapefile_path: 限制范围的矢量文件路径
        :param output_path: 输出图片保存路径
        """
        self.pred_dir = pred_dir
        self.true_dir = true_dir
        self.relativee_path = relativee_path
        self.shapefile_path = shapefile_path
        self.output_path = output_path

        # 定义土地类型名称
        self.land_type_names = {
            "Type1": "田地",
            "Type2": "林地",
            "Type3": "草原",
            "Type4": "水体",
            "Type5": "城市用地",
            "Type6": "农村住区",
            "Type7": "其他",
        }

        # 设置中文字体支持
        rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
        rcParams['axes.unicode_minus'] = False   # 解决负号显示问题

        # 读取矢量文件
        self.shape = gpd.read_file(self.shapefile_path)

    def _add_scale(self, ax, src_crs, ref_ax, length=50000, location=(0.5, 0.1), linewidth=3, fontsize=24):
        """
        添加比例尺，支持地理坐标系和投影坐标系
        :param ax: 要画比例尺的坐标区域 Axes实例
        :param src_crs: 栅格文件的坐标系
        :param ref_ax: 用于参考比例尺计算的坐标区域 Axes实例
        :param length: 比例尺长度（米）
        :param location: 比例尺位置，基于最后一个格子的左下角 (0, 0) 和右上角 (1, 1)
        :param linewidth: 比例尺线宽
        :param fontsize: 比例尺字体大小
        """
        # 获取最后一个图的坐标范围
        minx, maxx = ax.get_xlim()
        miny, maxy = ax.get_ylim()
        xlen = maxx - minx
        ylen = maxy - miny
    
        # 如果是地理坐标系（WGS84），使用经纬度计算比例尺
        if src_crs.is_geographic:
            center_lon = (minx + maxx) / 2
            center_lat = (miny + maxy) / 2
    
            # 使用 pyproj 计算比例尺长度对应的经度差
            geod = pyproj.Geod(ellps='WGS84')
            lon1, lat1, _ = geod.fwd(center_lon, center_lat, 90, length)  # 向东计算 length 米后的经度
            length_lon = lon1 - center_lon
        else:
            # 如果是投影坐标系，直接使用投影单位计算比例尺
            length_lon = length / xlen * (maxx - minx)  # 根据坐标范围缩放比例尺长度
    
        # 计算比例尺线的起点和终点
        x_start = minx + xlen * location[0]
        y_start = miny + ylen * location[1]
        x_end = x_start + length_lon
    
        # 绘制比例尺横线到目标轴
        ax.plot([x_start, x_end], [y_start, y_start], color='k', linewidth=linewidth)
    
        # 绘制比例尺文字到目标轴
        ax.text((x_start + x_end) / 2, y_start - ylen * 0.02 + 0.1, f'{round(length / 1000, 0)} km', fontsize=fontsize, ha='center')

    def _plot_raster(self, raster_path, ax, title):
        """
        绘制单个栅格文件的热力图，限制范围为矢量文件内
        :param raster_path: 栅格文件路径
        :param ax: 子图对象
        :param title: 图标题
        """
        with rasterio.open(raster_path) as src:
            data = src.read(1)  # 读取第一波段数据
            extent = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]  # 获取坐标范围

            # 将 -1 的 nodata 值替换为 NaN
            data = np.where(data == -1, np.nan, data)

            # 创建掩膜，限制范围为矢量文件内
            mask = geometry_mask(
                self.shape.geometry, transform=src.transform, invert=True, out_shape=data.shape
            )
            data = np.where(mask, data, np.nan)  # 将范围外的数据设置为 NaN

            # 绘制热力图
            ax.imshow(data, cmap="YlGnBu", extent=extent, origin="upper", vmin=0, vmax=1)  # 设置范围为 0-1
            ax.set_title(title, fontsize=24)
            ax.tick_params(labelsize=20)
            ax.grid()

            # 返回栅格文件的坐标系和数据范围
            return src.crs, np.nanmin(data), np.nanmax(data)

    def _plot_scale_and_legend(self, ax, src_crs, ref_ax, length=50000, location=(0.5, 0.1)):
        """
        绘制比例尺和矢量文件
        :param ax: 子图对象
        :param src_crs: 栅格文件的坐标系
        :param ref_ax: 用于参考比例尺计算的坐标区域 Axes实例
        :param length: 比例尺长度（米）
        :param location: 比例尺位置，基于最后一个格子的左下角 (0, 0) 和右上角 (1, 1)
        """
        ax.set_title(" ", fontsize=24)
        ax.axis("off")
    
        # 绘制矢量文件，设置线条透明
        self.shape.plot(ax=ax, edgecolor="none", alpha=0.0)
    
        # 绘制比例尺
        self._add_scale(ax, src_crs, ref_ax, length=length, location=location, linewidth=3, fontsize=24)

        # 添加指南针
        self._add_north(ax, labelsize=34, loc_x=0.5, loc_y=0.55, width=0.18, height=0.35, pad=0.14)
    
    def _add_north(self, ax, labelsize=34, loc_x=0.5, loc_y=0.55, width=0.18, height=0.40, pad=0.14):
        """
        绘制指南针
        """
        minx, maxx = ax.get_xlim()
        miny, maxy = ax.get_ylim()
        ylen = maxy - miny
        xlen = maxx - minx
        left = [minx + xlen * (loc_x - width * .5), miny + ylen * (loc_y - pad)]
        right = [minx + xlen * (loc_x + width * .5), miny + ylen * (loc_y - pad)]
        top = [minx + xlen * loc_x, miny + ylen * (loc_y - pad + height)]
        center = [minx + xlen * loc_x, left[1] + (top[1] - left[1]) * .4]
        triangle = mpatches.Polygon([left, top, right, center], color='k')
        ax.text(s='N',
                x=minx + xlen * loc_x,
                y=miny + ylen * (loc_y - pad + height),
                fontsize=labelsize,
                horizontalalignment='center',
                verticalalignment='bottom')
        ax.add_patch(triangle)

    def visualize(self):
        """
        绘制土地利用预测值与真实值的可视化图组
        """
        # 获取预测值和真实值文件列表
        pred_files = sorted([f for f in os.listdir(self.pred_dir) if f.endswith(".tif")])
        true_files = sorted([f for f in os.listdir(self.true_dir) if f.endswith(".tif")])
    
        # 创建图形
        fig, axes = plt.subplots(4, 4, figsize=(24, 20))  # 增加图形大小
        plt.subplots_adjust(wspace=0.4, hspace=0.4)  # 增加子图间距
        axes = axes.flatten()
    
        # 绘制预测值和真实值
        vmin, vmax = 0, 1  # 设置全局范围为 0-1
        for i, (pred_file, true_file) in enumerate(zip(pred_files, true_files)):
            # 预测值
            pred_path = os.path.join(self.pred_dir, pred_file)
            src_crs, _, _ = self._plot_raster(pred_path, axes[2 * i], f"预测值 - {self.land_type_names[f'Type{i + 1}']}")

            # 真实值
            true_path = os.path.join(self.true_dir, true_file)
            self._plot_raster(true_path, axes[2 * i + 1], f"真实值 - {self.land_type_names[f'Type{i + 1}']}")
    
        # 绘制相对误差图
        src_crs, _, _ = self._plot_raster(self.relativee_path, axes[-2], "相对误差")  # 获取坐标系
    
        # 绘制最后一个图的矢量文件和比例尺
        self._plot_scale_and_legend(axes[-1], src_crs, axes[-2], length=50000, location=(0.32, 0.1))
    
        # 添加统一图例到最后一个格子
        norm = plt.Normalize(vmin=vmin, vmax=vmax)
        sm = plt.cm.ScalarMappable(cmap="YlGnBu", norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=axes[-1], orientation="horizontal", fraction=0.05, pad=0.05)  # 调整图例位置
        cbar.set_label("栅格值", fontsize=20)  # 设置图例字体大小
        cbar.ax.tick_params(labelsize=20)  # 设置图例刻度字体大小
    
        # 调整布局并保存图片
        plt.tight_layout()
        plt.savefig(self.output_path, dpi=300)

if __name__ == "__main__":
    # pred_dir = r"F:\landuse\app\MCCA\20230712-MCCA\TestData\output\pred2015"
    pred_dir = r"F:\landuse\app\MCCA\20230712-MCCA\TestData\output\pred2015-2"
    true_dir = r"F:\landuse\app\MCCA\20230712-MCCA\TestData\output\true2015"
    relativee_path = r"F:\landuse\app\MCCA\20230712-MCCA\TestData\output\relativee\relativee1015.tif"
    shapefile_path = r"F:\landuse\app\MCCA\20230712-MCCA\TestData\MixedLanduse_Shapefile\Xianning.shp"
    output_path = r"F:\landuse\app\MCCA\20230712-MCCA\TestData\output\土地利用可视化图组.png"

    # 调整图形大小和间距
    fig, axes = plt.subplots(4, 4, figsize=(24, 20))  # 增加图形大小
    plt.subplots_adjust(wspace=0.4, hspace=0.4)  # 增加子图间距

    visualizer = LandUseVisualizer(pred_dir, true_dir, relativee_path, shapefile_path, output_path)
    visualizer.visualize()