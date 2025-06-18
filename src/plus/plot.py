import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import colors
from matplotlib import rcParams


def plothotmap(filepath, title, outputdir):
    """
    绘制土地覆盖类型贡献度热力图
    """

    # 设置中文字体支持
    rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
    rcParams['axes.unicode_minus'] = False   # 解决负号显示问题

    # 读取 CSV 文件
    data = pd.read_csv(filepath)

    # 去掉总和行
    data = data[data["土地覆盖类型"] != "总和"]

    # 提取行标签和列标签
    row_labels = data["土地覆盖类型"]
    col_labels = data.columns[1:]

    # 提取矩阵数据并归一化
    matrix = data.iloc[:, 1:].values
    norm = colors.Normalize(vmin=matrix.min(), vmax=matrix.max())

    # 创建热力图
    plt.figure(figsize=(12, 8))
    ax = sns.heatmap(matrix, annot=True, fmt=".3g", cmap="YlGnBu", 
                    xticklabels=col_labels, yticklabels=row_labels, 
                    norm=norm, cbar_kws={"label": "贡献度"})

    # 设置 x 轴标签倾斜 45 度
    plt.xticks(rotation=45)

    # 添加标题
    plt.title(title, fontsize=16)

    # 显示图例
    # plt.colorbar(ax.collections[0], ax=ax, orientation="vertical")

    # 保存或显示图
    plt.tight_layout()
    plt.savefig(f"{outputdir}/{title}.png", dpi=300)
    plt.show()

if __name__ == "__main__":
    filepath = r"F:/landuse/data/unsignedchar/贡献度矩阵.csv"
    outputdir = r"F:/landuse/data/unsignedchar"
    title = "佛山市土地覆盖类型贡献度热力图(2015-2020)"
    plothotmap(filepath, title, outputdir)