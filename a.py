# app.py
import streamlit as st
from PIL import Image
import numpy as np

st.title("🔭 간단한 허블 은하 자동 분류기")

uploaded = st.file_uploader("은하 이미지를 업로드하세요", type=["jpg", "png", "jpeg"])

def classify_galaxy(image: Image.Image) -> str:
    """
    단순 자동 분류 함수 (색상과 형태 기반)
    실제 AI 모델이 아닌, 간단한 규칙 기반 예시.
    """
    img = image.convert("L").resize((64, 64))   # 흑백 축소
    arr = np.array(img)

    # 1. 밝기 분포 (중앙집중도)
    center = arr[24:40, 24:40].mean()
    edge = np.concatenate([arr[:8, :].flatten(), arr[-8:, :].flatten(),
                           arr[:, :8].flatten(), arr[:, -8:].flatten()]).mean()
    brightness_ratio = center / (edge + 1e-6)

    # 2. 색상 대비 (색이 복잡할수록 불규칙/나선 가능성)
    color_var = np.std(np.array(image.resize((64,64))))

    # 규칙 기반 판정
    if brightness_ratio > 1.5 and color_var < 40:
        # 중심이 밝고 색 변화가 적으면 → 타원은하
        e_index = min(7, int((brightness_ratio - 1.5) * 3))
        return f"타원은하 (E{e_index})"
    elif color_var > 50:
        # 색 대비 크면 → 불규칙은하
        return "불규칙은하 (Irr)"
    else:
        # 중간 정도면 → 나선은하
        subtype = np.random.choice(["Sa", "Sb", "Sc", "SBa", "SBb", "SBc"])
        return f"나선은하 ({subtype})"

if uploaded:
    img = Image.open(uploaded)
    st.image(img, caption="업로드된 은하", use_column_width=True)

    st.markdown("### 🔹 자동 분류 결과")
    result = classify_galaxy(img)
    st.success(f"예측된 분류: **{result}**")

    st.text_area("비고", placeholder="관측 소감이나 특징을 기록하세요.")
    st.button("결과 저장")
else:
    st.info("은하 이미지를 업로드하면 자동으로 분류됩니다.")
