import math
from typing import NamedTuple

import gwv.filters as filters
from gwv.helper import isYoko
from gwv.validatorctx import ValidatorContext
from gwv.validators import Validator, ValidatorErrorEnum, error_code


class SkewError(NamedTuple):
    line: list  # kage line number and data


class SkewErrorAngle(NamedTuple):
    line: list  # kage line number and data
    angle: float


class SkewValidatorError(ValidatorErrorEnum):
    @error_code("10")
    class SKEWED_HORI_LINE(SkewErrorAngle):
        """歪んだ水平"""
    @error_code("11")
    class SKEWED_VERT_LINE(SkewErrorAngle):
        """歪んだ垂直"""
    @error_code("30")
    class SKEWED_HORI_ORE_LAST(SkewErrorAngle):
        """折れの後半が歪んだ水平"""
    @error_code("31")
    class SKEWED_VERT_ORE_FIRST(SkewErrorAngle):
        """折れの前半が歪んだ垂直"""
    @error_code("40")
    class SKEWED_HORI_OTSU_LAST(SkewErrorAngle):
        """乙の後半が歪んだ水平"""
    @error_code("70")
    class HORI_TATEBARAI_FIRST(SkewError):
        """縦払いの直線部分が横"""
    @error_code("71")
    class SNAPPED_TATEBARAI(SkewErrorAngle):
        """曲がった縦払い"""
    @error_code("72")
    class SKEWED_VERT_TATEBARAI_FIRST(SkewErrorAngle):
        """縦払いの直線部分が歪んだ垂直"""


E = SkewValidatorError


class SkewValidator(Validator):

    @filters.check_only(-filters.is_alias)
    @filters.check_only(-filters.is_of_category({"user-owned"}))
    def is_invalid(self, ctx: ValidatorContext):
        for line in ctx.glyph.kage.lines:
            stype = line.stroke_type
            coords = line.coords
            if stype == 1:
                xDif = abs(coords[0][0] - coords[1][0])
                yDif = abs(coords[0][1] - coords[1][1])
                if xDif <= yDif and xDif != 0 and xDif <= 3:
                    # 歪んだ垂直
                    return E.SKEWED_VERT_LINE(
                        [line.line_number, line.strdata],
                        round(math.atan2(xDif, yDif) * 180 / math.pi, 1))
                if xDif > yDif and yDif != 0 and yDif <= 3:
                    # 歪んだ水平
                    return E.SKEWED_HORI_LINE(
                        [line.line_number, line.strdata],
                        round(math.atan2(yDif, xDif) * 180 / math.pi, 1))
            elif stype == 3:
                xDif1 = abs(coords[0][0] - coords[1][0])
                yDif1 = abs(coords[0][1] - coords[1][1])
                if xDif1 != 0 and xDif1 <= 3:
                    # 折れの前半が歪んだ垂直
                    return E.SKEWED_VERT_ORE_FIRST(
                        [line.line_number, line.strdata],
                        round(math.atan2(xDif1, yDif1) * 180 / math.pi, 1))
                xDif2 = abs(coords[1][0] - coords[2][0])
                yDif2 = abs(coords[1][1] - coords[2][1])
                if yDif2 != 0 and yDif2 <= 3:
                    # 折れの後半が歪んだ水平
                    return E.SKEWED_HORI_ORE_LAST(
                        [line.line_number, line.strdata],
                        round(math.atan2(yDif2, xDif2) * 180 / math.pi, 1))
            elif stype == 4:
                xDif = abs(coords[1][0] - coords[2][0])
                yDif = abs(coords[1][1] - coords[2][1])
                if yDif != 0 and yDif <= 3:
                    # 乙の後半が歪んだ水平
                    return E.SKEWED_HORI_OTSU_LAST(
                        [line.line_number, line.strdata],
                        round(math.atan2(yDif, xDif) * 180 / math.pi, 1))
            elif stype == 7:
                if isYoko(*coords[0], *coords[1]):
                    # 縦払いの直線部分が横
                    return E.HORI_TATEBARAI_FIRST(
                        [line.line_number, line.strdata])
                xDif1 = coords[1][0] - coords[0][0]
                yDif1 = coords[1][1] - coords[0][1]
                theta1 = math.atan2(yDif1, xDif1)
                if xDif1 == 0 and yDif1 == 0:
                    theta1 = math.pi / 2
                xDif2 = coords[2][0] - coords[1][0]
                yDif2 = coords[2][1] - coords[1][1]
                theta2 = math.atan2(yDif2, xDif2)
                if (xDif1 == 0 and xDif2 != 0) or \
                        abs(theta1 - theta2) * 60 > 3:
                    # 曲がった縦払い
                    return E.SNAPPED_TATEBARAI(
                        [line.line_number, line.strdata],
                        round(abs(theta1 - theta2) * 180 / math.pi, 1))
                if xDif1 != 0 and -3 <= xDif1 <= 3:
                    # 縦払いの直線部分が歪んだ垂直
                    return E.SKEWED_VERT_TATEBARAI_FIRST(
                        [line.line_number, line.strdata],
                        round(abs(90 - theta1 * 180 / math.pi), 1))
        return False

    def get_result(self):
        for key, val in self.results.items():
            if key != E.HORI_TATEBARAI_FIRST.errcode:
                # 歪み角度が大きい順にソート
                val.sort(key=lambda r: r[2], reverse=True)
        return super(SkewValidator, self).get_result()
