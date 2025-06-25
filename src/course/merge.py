import os
from PIL import Image

class ImageMerger:
    def __init__(self, input_folder, output_folder):
        """
        初始化图片拼接类
        :param input_folder: 输入图片文件夹路径
        :param output_folder: 输出图片文件夹路径
        """
        self.input_folder = input_folder
        self.output_folder = output_folder

        # 定义拼接组
        self.groups = {
            "PD": "PD_merged.png",
            "ED": "ED_merged.png",
            "CONTAG_LPI_SHDI": "CONTAG_LPI_SHDI_merged.png"
        }

    def _get_images_by_prefix(self, prefix):
        """
        获取指定前缀的图片文件列表
        :param prefix: 图片文件名前缀
        :return: 图片文件路径列表
        """
        return sorted([os.path.join(self.input_folder, f) for f in os.listdir(self.input_folder) if f.startswith(prefix) and f.endswith(".png")])

    def _merge_images(self, image_paths, output_path, layout="2x3"):
        """
        拼接图片
        :param image_paths: 图片文件路径列表
        :param output_path: 输出图片路径
        :param layout: 拼接布局 ("2x3" 或 "1x3")
        """
        # 打开所有图片
        images = [Image.open(img_path) for img_path in image_paths]

        # 获取单张图片的宽度和高度
        width, height = images[0].size

        if layout == "2x3":
            # 设置拼接后的图片宽度和高度（横向2，纵向3）
            merged_width = width * 2
            merged_height = height * 3
        elif layout == "1x3":
            # 设置拼接后的图片宽度和高度（纵向3）
            merged_width = width
            merged_height = height * 3
        else:
            raise ValueError(f"未知布局类型: {layout}")

        # 创建空白画布
        merged_image = Image.new("RGB", (merged_width, merged_height), (255, 255, 255))

        # 将图片逐一粘贴到画布上
        for idx, img in enumerate(images):
            if layout == "2x3":
                x_offset = (idx % 2) * width  # 横向偏移
                y_offset = (idx // 2) * height  # 纵向偏移
            elif layout == "1x3":
                x_offset = 0  # 横向偏移固定为 0
                y_offset = idx * height  # 纵向偏移
            merged_image.paste(img, (x_offset, y_offset))

        # 保存拼接后的图片
        merged_image.save(output_path)

    def merge_all(self):
        """
        拼接所有图片组
        """
        for prefix, output_filename in self.groups.items():
            if prefix == "CONTAG_LPI_SHDI":
                # 拼接 CONTAG, LPI, SHDI 图片
                image_paths = []
                for metric in ["CONTAG", "LPI", "SHDI"]:
                    image_paths.extend(self._get_images_by_prefix(metric))
            else:
                # 拼接 PD 或 ED 图片
                image_paths = self._get_images_by_prefix(prefix)

            # 检查图片数量
            if prefix == "CONTAG_LPI_SHDI" and len(image_paths) == 3:
                layout = "1x3"  # 纵向拼接
            elif len(image_paths) == 6:
                layout = "2x3"  # 横向2，纵向3拼接
            else:
                raise ValueError(f"图片组 '{prefix}' 中的图片数量不符合要求，当前数量为 {len(image_paths)}")

            # 设置输出路径
            output_path = os.path.join(self.output_folder, output_filename)

            # 拼接图片
            self._merge_images(image_paths, output_path, layout)


if __name__ == "__main__":
    # 输入文件夹路径
    input_folder = r"F:\landuse\data\unsignedchar\homework\visualizations\landscape"
    output_folder = r"F:\landuse\data\unsignedchar\homework\visualizations\merged"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 初始化图片拼接器并执行任务
    merger = ImageMerger(input_folder, output_folder)
    merger.merge_all()
