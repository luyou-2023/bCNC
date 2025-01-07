import numpy
from svgelements import SVG, Arc, Close, Line, Move, Path, Shape

# 定义一个将 SVG 路径数据转换为 G-code 的类
class SVGcode:
    def __init__(self, filepath=None):
        """
        初始化类，接受一个 SVG 文件的路径。

        :param filepath: SVG 文件的路径
        """
        self._filepath = filepath

    def path2gcode(self, path, samples_per_unit=100, d=4):
        """
        将 SVG 的路径数据转换为 G-code。

        :param path: SVG 路径（可以是字符串或 `Path` 对象）
        :param samples_per_unit: 每单位长度的采样点数（控制精度）
        :param d: G-code 数字的保留小数位数
        :return: 对应的 G-code 字符串
        """
        gcode = []  # 用于存储 G-code 的列表

        # 如果路径是字符串，将其解析为 Path 对象
        if isinstance(path, str):
            path = Path(path)

        # 定义一个辅助函数，将数字格式化为保留 d 位小数的字符串
        def rv(v):
            return (f"{round(v, d):{d}}").rstrip("0").rstrip(".")

        # 遍历路径中的每个段（`Move`、`Line`、`Arc` 等）
        for segment in path:
            # 计算每段的采样点数（基于段的长度）
            subdiv = max(1, round(segment.length(error=1e-5) * samples_per_unit))

            # 如果段是一个移动（`Move`），生成快速移动的 G-code
            if isinstance(segment, Move):
                gcode.append(f"G0 X{rv(segment.end.x)} Y{rv(-segment.end.y)}")
            # 如果段是直线（`Line`）或闭合路径（`Close`），生成线性移动的 G-code
            elif isinstance(segment, (Line, Close)):
                gcode.append(f"G1 X{rv(segment.end.x)} Y{rv(-segment.end.y)}")
            # 如果段是圆弧（`Arc`），且是圆形弧线（半径在 x 和 y 方向相等）
            elif (isinstance(segment, Arc) and abs(segment.rx - segment.ry) < 1e-9):
                # 判断弧线是顺时针（`G02`）还是逆时针（`G03`）
                garc = "G02" if segment.sweep > 0 else "G03"
                # 生成弧线的 G-code
                gcode.append(" ".join([
                    f"{garc}", f"X{rv(segment.end.x)}",
                    f"Y{rv(-segment.end.y)}", f"R{rv(segment.rx)}"
                ]))
            else:
                # 非圆形弧线（如椭圆）、贝塞尔曲线（包括三次和二次）
                # 使用分段点近似生成线段的 G-code
                subdiv_points = numpy.linspace(0, 1, subdiv, endpoint=True)[1:]
                # 通过点的采样计算每个分段点的坐标
                points = segment.npoint(subdiv_points)
                # 为每个分段点生成线性移动的 G-code
                gcode.extend(
                    [f"G1 X{rv(sp[0])} Y{rv(-sp[1])}" for sp in points]
                )

        return "\n".join(gcode)  # 将所有 G-code 行拼接为一个字符串返回

    def get_gcode(self, scale=1.0 / 96.0, samples_per_unit=100, digits=4, ppi=96.0):
        """
        从 SVG 文件解析 G-code。

        :param scale: 单位比例，将 SVG 像素转换为目标单位（默认 1.0/96.0 表示英寸）
        :param samples_per_unit: 每单位长度的采样点数（控制精度）
        :param digits: G-code 精度（保留小数位数）
        :param ppi: 每英寸像素数（通常 96 是标准值）
        :return: 包含 G-code 数据的列表，每个元素是一个字典
        """
        gcode = []  # 用于存储 G-code 的列表

        # 如果需要缩放，应用 `scale` 变换
        transform = f"scale({scale:g})" if scale != 1.0 else None

        # 使用 `svgelements` 加载并解析 SVG 文件
        svg = SVG.parse(self._filepath, reify=False, ppi=ppi, transform=transform)

        # 遍历 SVG 的所有元素
        for element in svg.elements():
            # 如果元素是可绘制的形状（`Shape`），则进行处理
            if isinstance(element, Shape):
                # 如果元素不是路径（`Path`），则转换为路径
                if not isinstance(element, Path):
                    element = Path(element)
                # 生成对应的 G-code 并保存到列表中
                gcode.append(
                    {
                        "id": element.id,  # SVG 元素的 ID
                        "path": self.path2gcode(
                            element.reify(), samples_per_unit, digits
                        ),  # 生成的 G-code 路径
                    }
                )
        return gcode  # 返回包含 G-code 的列表
