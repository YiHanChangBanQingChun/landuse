import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams
import seaborn as sns

class LandscapePatternVisualizer:
    def __init__(self, excel_path, output_folder):
        """
        初始化景观格局可视化类
        :param excel_path: Excel 文件路径
        :param output_folder: 输出图片保存路径
        """
        self.excel_path = excel_path
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

        # 定义指标
        self.metrics = ["SHDI", "LPI", "CONTAG", "PD_1", "ED_1", "PD_2", "ED_2", "PD_3", "ED_3", "PD_4", "ED_4", "PD_5", "ED_5", "PD_6", "ED_6"]

        # 加载 Excel 数据
        self.data = self._load_excel()

    def _load_excel(self):
        """
        加载 Excel 文件中的三个小表
        :return: 包含三个时间的数据的字典
        """
        sheets = ["表2015", "表2020", "表2030"]
        data = {}
        for sheet in sheets:
            data[sheet] = pd.read_excel(self.excel_path, sheet_name=sheet)
        return data

    def _annotate_statistics(self, ax, data, metric):
        """
        在对应子图的下方标注均值和方差
        :param ax: 子图对象
        :param data: 数据
        :param metric: 指标名称
        """
        mean = round(data[metric].mean(), 2)
        std = round(data[metric].std(), 2)
        annotation = f"均值: {mean}, 方差: {std}"
        ax.text(0.5, -0.15, annotation, fontsize=18, ha="center", transform=ax.transAxes)

    def _plot_violin(self, metric, output_path):
        """
        绘制小提琴图
        :param metric: 指标名称
        :param output_path: 输出图片路径
        """
        # 准备数据
        data = [self.data["表2015"], self.data["表2020"], self.data["表2030"]]
        time_labels = ["2015年", "2020年", "2030年"]

        # 创建图形，确保每个子图长宽比为 4:3
        fig, axes = plt.subplots(1, 3, figsize=(12, 9), sharey=True)  # 每个子图长宽比为 4:3
        plt.subplots_adjust(wspace=0.4)

        # 绘制每个时间的小提琴图
        for i, (ax, time_label, d) in enumerate(zip(axes, time_labels, data)):
            sns.violinplot(data=d, y=metric, ax=ax, inner="quartile", hue=None, palette="muted", legend=False)
            ax.set_title(f"{time_label}", fontsize=24)
            ax.set_xlabel("")
            ax.set_ylabel(metric, fontsize=21)
            # 把y轴标注数字调大
            ax.tick_params(axis='y', labelsize=18)

            # 添加均值和方差标注到对应子图下方
            self._annotate_statistics(ax, d, metric)

        # 设置总标题
        if "_" in metric:
            land_cover_type = self.land_cover_types[int(metric.split("_")[1])]
            fig.suptitle(f"{metric.split('_')[0]} ({land_cover_type})", fontsize=30)
        else:
            fig.suptitle(metric, fontsize=30)

        # 保存图片
        plt.tight_layout(rect=[0, 0, 1, 0.95])  # 调整布局以适应标题
        plt.savefig(output_path, dpi=300)
        plt.close(fig)

    def visualize(self):
        """
        绘制所有指标的小提琴图
        """
        for metric in self.metrics:
            # 检查是否是土地覆盖相关指标
            if "_" in metric:
                land_cover_type = self.land_cover_types[int(metric.split("_")[1])]
                metric_label = f"{metric.split('_')[0]} ({land_cover_type})"  # 去掉数字，仅保留土地类型名字
            else:
                metric_label = metric

            # 设置输出路径
            output_path = os.path.join(self.output_folder, f"{metric_label}_violin.png")

            # 绘制小提琴图
            self._plot_violin(metric, output_path)


if __name__ == "__main__":
    # 文件路径
    excel_path = r"F:\landuse\doc\大作业152030景观格局.xlsx"
    output_folder = r"F:\landuse\data\unsignedchar\homework\visualizations\landscape"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 初始化可视化器并执行任务
    visualizer = LandscapePatternVisualizer(excel_path, output_folder)
    visualizer.visualize()