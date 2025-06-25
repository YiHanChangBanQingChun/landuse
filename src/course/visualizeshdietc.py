import os
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib import rcParams
import numpy as np

class MetricsVisualizer:
    def __init__(self, merged_folder, boundary_shapefile, output_folder):
        """
        初始化指标可视化类
        :param merged_folder: 合并后的 Shapefile 文件夹路径
        :param boundary_shapefile: 边界矢量文件路径
        :param output_folder: 输出图片保存路径
        """
        self.merged_folder = merged_folder
        self.boundary_shapefile = boundary_shapefile
        self.output_folder = output_folder

        # 设置中文字体支持
        rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
        rcParams['axes.unicode_minus'] = False   # 解决负号显示问题

        # 读取边界矢量文件并转换为 EPSG:4326
        self.boundary = gpd.read_file(self.boundary_shapefile).to_crs("EPSG:4326")

        # 定义年份和指标
        self.year_file_mapping = {
            "2015": "fishnet_metrics_2015_landcover_merged.shp",
            "2020": "fishnet_metrics_2020_landcover_merged.shp",
            "2030": "fishnet_metrics_2030_prediction_merged.shp"
        }
        self.metrics = ["SHDI", "LPI", "CONTAG"]

    def _plot_metric(self, gdf, metric, ax, title, show_frame=True):
        """
        绘制单个指标的热力图
        :param gdf: GeoDataFrame
        :param metric: 指标名称
        :param ax: 子图对象
        :param title: 图标题
        :param show_frame: 是否显示图框和坐标轴
        """
        # 转换为 EPSG:4326
        gdf = gdf.to_crs("EPSG:4326")

        # 绘制指标的热力图
        gdf.plot(column=metric, ax=ax, cmap="YlGnBu", legend=False, alpha=0.8)
        ax.set_title(title, fontsize=24)

        if show_frame:
            ax.tick_params(labelsize=16)
        else:
            ax.axis("off")

    def _calculate_difference(self, gdf1, gdf2, metric):
        """
        计算两个年份的指标差值
        :param gdf1: 第一个年份的 GeoDataFrame
        :param gdf2: 第二个年份的 GeoDataFrame
        :param metric: 指标名称
        :return: 差值 GeoDataFrame
        """
        gdf1 = gdf1.to_crs("EPSG:4326")
        gdf2 = gdf2.to_crs("EPSG:4326")
        gdf_diff = gdf1.copy()
        gdf_diff[metric] = gdf2[metric] - gdf1[metric]
        return gdf_diff

    def _add_legend(self, fig, ax, norm, cmap, label):
        """
        添加图例到页面下方的独立画布
        :param fig: 图形对象
        :param ax: 子图对象
        :param norm: 归一化对象
        :param cmap: 颜色映射
        :param label: 图例标签
        """
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.5, pad=0.2)
        cbar.set_label(label, fontsize=20)
        cbar.ax.tick_params(labelsize=16)

    def visualize(self):
        """
        绘制指标可视化图组
        """
        # 遍历每个指标
        for metric in self.metrics:
            # 创建主图形
            fig, axes = plt.subplots(2, 3, figsize=(24, 16))  # 2行3列布局
            plt.subplots_adjust(wspace=0.4, hspace=0.4)
            axes = axes.flatten()

            # 绘制每年的指标热力图
            gdfs = {}
            for i, (year, file_name) in enumerate(self.year_file_mapping.items()):
                file_path = os.path.join(self.merged_folder, file_name)
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"文件 {file_path} 不存在")
                gdfs[year] = gpd.read_file(file_path)
                self._plot_metric(gdfs[year], metric, axes[i], f"{year}年 {metric}", show_frame=True)

            # 计算差值并绘制差值图
            diff_15_20 = self._calculate_difference(gdfs["2015"], gdfs["2020"], metric)
            diff_20_30 = self._calculate_difference(gdfs["2020"], gdfs["2030"], metric)
            diff_15_30 = self._calculate_difference(gdfs["2015"], gdfs["2030"], metric)

            self._plot_metric(diff_15_20, metric, axes[3], "2015-2020差值", show_frame=True)
            self._plot_metric(diff_20_30, metric, axes[4], "2020-2030差值", show_frame=True)
            self._plot_metric(diff_15_30, metric, axes[5], "2015-2030差值", show_frame=True)

            # 创建两个独立的画布用于图例
            fig_legend, legend_axes = plt.subplots(1, 2, figsize=(24, 4))  # 两个小长画布
            plt.subplots_adjust(wspace=0.4)

            # 添加图例到独立画布，且两个独立画布不显示图框
            for ax in legend_axes:
                ax.axis("off")
            norm_metric = plt.Normalize(vmin=gdfs["2015"][metric].min(), vmax=gdfs["2030"][metric].max())
            norm_diff = plt.Normalize(vmin=diff_15_30[metric].min(), vmax=diff_15_30[metric].max())

            self._add_legend(fig_legend, legend_axes[0], norm_metric, cmap="YlGnBu", label=f"{metric} 值")
            self._add_legend(fig_legend, legend_axes[1], norm_diff, cmap="RdYlBu", label=f"{metric} 差值")

            # 保存主图和图例
            output_path_main = os.path.join(self.output_folder, f"{metric}_visualization.png")
            output_path_legend = os.path.join(self.output_folder, f"{metric}_legend.png")
            plt.tight_layout()
            fig.savefig(output_path_main, dpi=300)
            fig_legend.savefig(output_path_legend, dpi=300)
            plt.close(fig)
            plt.close(fig_legend)


if __name__ == "__main__":
    # 文件夹路径
    merged_folder = r"F:\landuse\data\unsignedchar\homework\merged"
    boundary_shapefile = r"F:\landuse\data\unsignedchar\homework\fishnet\佛山边界.shp"
    output_folder = r"F:\landuse\data\unsignedchar\homework\visualizations"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 初始化可视化器并执行任务
    visualizer = MetricsVisualizer(merged_folder, boundary_shapefile, output_folder)
    visualizer.visualize()