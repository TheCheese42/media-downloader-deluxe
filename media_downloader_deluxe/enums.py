from enum import IntEnum


class Type(IntEnum):
    Video = 0
    Music = 1
    VideoOnly = 2


class Quality(IntEnum):
    Best = 0
    Good = 1
    Normal = 2
    Bad = 3
    VeryBad = 4
    Worst = 5

    def is_quality(self, other):
        if isinstance(other, Quality):
            return True if self == other else False
        elif isinstance(other, MusicQuality):
            if self == self.Best:
                return True if other == MusicQuality.Best else False
            elif self == self.Normal:
                return True if other == MusicQuality.Normal else False
            elif self == self.Worst:
                return True if other == MusicQuality.Worst else False
            else:
                return False
        else:
            raise TypeError(f"Can't compare with {type(other)}")

    def to_standard(self):
        return self


class MusicQuality(IntEnum):
    Best = 0
    Normal = 1
    Worst = 2

    def is_quality(self, other):
        if isinstance(other, MusicQuality):
            return True if self == other else False
        elif isinstance(other, Quality):
            if self == self.Best:
                return True if other == Quality.Best else False
            if self == self.Normal:
                return True if other == Quality.Normal else False
            if self == self.Worst:
                return True if other == Quality.Worst else False
            else:
                return False
        else:
            raise TypeError(f"Can't compare with {type(other)}")

    def to_standard(self):
        if self == self.Best:
            return Quality.Best
        elif self == self.Normal:
            return Quality.Normal
        elif self == self.Worst:
            return Quality.Worst
