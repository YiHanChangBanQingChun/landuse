import os
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.gridspec import GridSpec
import numpy as np

class LandCoverVisualizer:
    def __init__(self, merged_folder, boundary_shapefile, output_folder):
        """
        初始化土地覆盖类型可视化类
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

        # 定义土地覆盖类型
        self.land_cover_types = {
            1: "耕地",
            2: "林地",
            3: "荒地",
            4: "草地",
            5: "水域",
            6: "不透水面"
        }

        # 定义年份和文件映射
        self.year_file_mapping = {
            "2015": "fishnet_metrics_2015_landcover_merged.shp",
            "2020": "fishnet_metrics_2020_landcover_merged.shp",
            "2030": "fishnet_metrics_2030_prediction_merged.shp"
        }

        # 读取边界矢量文件并转换为 EPSG:4326
        self.boundary = gpd.read_file(self.boundary_shapefile).to_crs("EPSG:4326")

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
        ax.set_title(title, fontsize=16)

        if show_frame:
            ax.tick_params(labelsize=12)
        else:
            ax.axis("off")

    def _add_colorbar(self, fig, norm, cmap, label, cbar_ax):
        """
        添加图例到指定位置
        :param fig: 图形对象
        :param norm: 归一化对象
        :param cmap: 颜色映射
        :param label: 图例标签
        :param cbar_ax: 图例的轴对象
        """
        # 创建颜色映射
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])

        # 添加颜色条到指定位置
        cbar = fig.colorbar(sm, cax=cbar_ax, orientation="vertical", fraction=0.5, pad=0.05)
        cbar.set_label(label, fontsize=14)
        cbar.ax.tick_params(labelsize=12)

    def visualize_land_cover(self):
        """
        可视化所有土地覆盖类型的指标热力图
        """
        for land_cover_id, land_cover_name in self.land_cover_types.items():
            # 创建主图形和布局
            fig = plt.figure(figsize=(18, 12))
            gs = GridSpec(2, 4, figure=fig, width_ratios=[1, 1, 1, 0.1])  # 最后一列用于图例

            # 创建子图
            axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(3)]

            # 图例轴
            pd_cbar_ax = fig.add_subplot(gs[0, 3])  # 第一行图例
            ed_cbar_ax = fig.add_subplot(gs[1, 3])  # 第二行图例，与 PD 图例对齐

            # 遍历年份
            for i, (year, file_name) in enumerate(self.year_file_mapping.items()):
                file_path = os.path.join(self.merged_folder, file_name)
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"文件 {file_path} 不存在")

                # 读取 Shapefile 数据
                gdf = gpd.read_file(file_path)

                # 绘制 PD 和 ED 指标的热力图
                self._plot_metric(gdf, f"PD_{land_cover_id}", axes[i], f"{year}年 {land_cover_name} PD", show_frame=True)
                self._plot_metric(gdf, f"ED_{land_cover_id}", axes[i + 3], f"{year}年 {land_cover_name} ED", show_frame=True)

            # 添加 PD 图例到右侧
            pd_norm = plt.Normalize(vmin=gdf[f"PD_{land_cover_id}"].min(), vmax=gdf[f"PD_{land_cover_id}"].max())
            self._add_colorbar(fig, pd_norm, cmap="YlGnBu", label=f"{land_cover_name} PD 值", cbar_ax=pd_cbar_ax)

            # 添加 ED 图例到右侧
            ed_norm = plt.Normalize(vmin=gdf[f"ED_{land_cover_id}"].min(), vmax=gdf[f"ED_{land_cover_id}"].max())
            self._add_colorbar(fig, ed_norm, cmap="YlGnBu", label=f"{land_cover_name} ED 值", cbar_ax=ed_cbar_ax)

            # 设置总标题
            fig.suptitle(f"{land_cover_name} 指标热力图", fontsize=20)

            # 保存图片
            output_path = os.path.join(self.output_folder, f"{land_cover_name}_heatmap.png")
            plt.tight_layout(rect=[0, 0, 0.95, 0.95])  # 调整布局以适应标题和图例
            plt.savefig(output_path, dpi=300)
            plt.close(fig)


if __name__ == "__main__":
    # 文件夹路径
    merged_folder = r"F:\landuse\data\unsignedchar\homework\merged"
    boundary_shapefile = r"F:\landuse\data\unsignedchar\homework\fishnet\佛山边界.shp"
    output_folder = r"F:\landuse\data\unsignedchar\homework\visualizations\land_cover"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 初始化可视化器并执行任务
    visualizer = LandCoverVisualizer(merged_folder, boundary_shapefile, output_folder)
    visualizer.visualize_land_cover()