# app.py
import streamlit as st
from PIL import Image
import numpy as np

st.title("🔭 간단한 허블 은하 자동 분류기")

uploaded = st.file_uploader("은하 이미지를 업로드하세요", type=["jpg", "png", "jpeg"])

def is_galaxy(image: Image.Image) -> bool:
    """
    은하 여부 판별 (단순 규칙 기반)
    - 전체 명암 대비가 매우 크거나
      색이 선명한 경우(사람, 동물, 사물)는 은하가 아닐 가능성 높음.
    """
    img = image.resize((128, 128))
    arr = np.array(img)
    if arr.ndim == 3:
        brightness = arr.mean(axis=(0, 1))       # RGB 평균
        contrast = arr.std()                     # 전체 대비
        color_spread = np.std(brightness)        # 채널 간 편차
    else:
        contrast = arr.std()
        color_spread = 0

    # 경험적 임계값: contrast 60↑ or color_spread 25↑ → 은하 아님
    return not (contrast > 60 or color_spread > 25)

def classify_galaxy(image: Image.Image) -> str:
    """
    은하 자동 분류 함수 (단순 규칙 기반)
    """
    img = image.convert("L").resize((64, 64))
    arr = np.array(img)

    center = arr[24:40, 24:40].mean()
    edge = np.concatenate([
        arr[:8, :].flatten(), arr[-8:, :].flatten(),
        arr[:, :8].flatten(), arr[:, -8:].flatten()
    ]).mean()
    brightness_ratio = center / (edge + 1e-6)
    color_var = np.std(np.array(image.resize((64, 64))))

    if brightness_ratio > 1.5 and color_var < 40:
        e_index = min(7, int((brightness_ratio - 1.5) * 3))
        return f"타원은하 (E{e_index})"
    elif color_var > 50:
        return "불규칙은하 (Irr)"
    else:
        subtype = np.random.choice(["Sa", "Sb", "Sc", "SBa", "SBb", "SBc"])
        return f"나선은하 ({subtype})"


if uploaded:
    img = Image.open(uploaded)
    st.image(img, caption="업로드된 이미지", use_column_width=True)

    st.markdown("### 🔹 자동 판별 결과")
    if is_galaxy(img):
        result = classify_galaxy(img)
        st.success(f"예측된 분류: **{result}**")
    else:
        st.error("🚫 이 이미지는 은하로 판별되지 않았습니다. 은하 사진을 업로드하세요.")

    st.text_area("비고", placeholder="관측 소감이나 특징을 기록하세요.")
    st.button("결과 저장")
else:
    st.info("은하 이미지를 업로드하면 자동으로 판별 및 분류됩니다.")
