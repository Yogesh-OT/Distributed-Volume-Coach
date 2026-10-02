"""Body profile: plain descriptions from tape-and-scale measurements.

Nothing here assigns an ecto/meso/endo type, and nothing here changes a plan.
"""

from dataclasses import dataclass

# height / wrist (cm). Values above `small` are a small frame, below `large` a large one.
FRAME_THRESHOLDS = {
    "male": {"small": 10.4, "large": 9.6},
    "female": {"small": 11.0, "large": 10.1},
}


@dataclass(frozen=True)
class BodyInput:
    height_cm: float | None = None
    weight_kg: float | None = None
    arm_span_cm: float | None = None
    waist_cm: float | None = None
    wrist_cm: float | None = None
    sex: str | None = None  # "male", "female" or None


@dataclass(frozen=True)
class ProfileLine:
    key: str
    label: str  # the measurement, e.g. "Arm span 178"
    headline: str  # what it means, e.g. "Long arms for your height (1.03)"
    detail: str
    value: float | None = None  # the derived ratio, when there is one


def _num(x: float) -> str:
    return f"{x:g}"


def ape_index(arm_span_cm: float, height_cm: float) -> float:
    return round(arm_span_cm / height_cm, 2)


def waist_to_height(waist_cm: float, height_cm: float) -> float:
    return round(waist_cm / height_cm, 2)


def frame_size(height_cm: float, wrist_cm: float, sex: str) -> str:
    t = FRAME_THRESHOLDS[sex]
    index = height_cm / wrist_cm
    if index > t["small"]:
        return "small"
    if index < t["large"]:
        return "large"
    return "medium"


def body_profile(b: BodyInput) -> list[ProfileLine]:
    lines: list[ProfileLine] = []
    h = b.height_cm

    if h is not None:
        label = f"{_num(h)} cm" + (f" · {_num(b.weight_kg)} kg" if b.weight_kg is not None else "")
        lines.append(ProfileLine("size", label, "Height and weight", "Weight is re-checked weekly."))

    if h is not None and b.arm_span_cm is not None:
        ratio = ape_index(b.arm_span_cm, h)
        if ratio > 1.02:
            headline = f"Long arms for your height ({ratio:.2f})"
            detail = "Push-ups cost a little more per rep, so slower rep gains are normal for you."
        elif ratio < 0.98:
            headline = f"Short arms for your height ({ratio:.2f})"
            detail = "Push-ups have a shorter range for you, so each rep costs a little less."
        else:
            headline = f"Typical arm length for your height ({ratio:.2f})"
            detail = "Push-ups cost a typical amount per rep for your size."
        lines.append(ProfileLine("ape_index", f"Arm span {_num(b.arm_span_cm)}", headline, detail, ratio))

    if h is not None and b.waist_cm is not None:
        ratio = waist_to_height(b.waist_cm, h)
        if ratio < 0.5:
            detail = "Under the usual 0.5 guide."
        elif ratio < 0.6:
            detail = "Above the usual 0.5 guide. It tends to come down with regular activity and diet changes."
        else:
            detail = "Well above the usual 0.5 guide. Worth raising with a doctor at your next check-up."
        lines.append(ProfileLine("waist_ratio", f"Waist {_num(b.waist_cm)}", f"{ratio:.2f} of your height", detail, ratio))

    if h is not None and b.wrist_cm is not None:
        sexes = [b.sex] if b.sex in FRAME_THRESHOLDS else list(FRAME_THRESHOLDS)
        sizes = sorted({frame_size(h, b.wrist_cm, s) for s in sexes}, key=["small", "medium", "large"].index)
        detail = "Describes bone size. It doesn't change your plan."
        if len(sizes) == 1:
            headline = f"{sizes[0].capitalize()} frame"
        else:
            headline = f"{sizes[0].capitalize()} to {sizes[-1]} frame"
            detail += " Add sex to your profile for a narrower range."
        lines.append(ProfileLine("frame", f"Wrist {_num(b.wrist_cm)}", headline, detail, round(h / b.wrist_cm, 2)))

    return lines
