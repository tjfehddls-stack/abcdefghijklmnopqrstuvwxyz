# app.py
import streamlit as st
from PIL import Image

st.title("🔭 간단한 허블 은하 분류기")

uploaded = st.file_uploader("은하 이미지를 업로드하세요", type=["jpg", "png", "jpeg"])
if uploaded:
    img = Image.open(uploaded)
    st.image(img, caption="업로드된 은하", use_column_width=True)

    st.markdown("### 🔹 분류 선택")
    class_type = st.radio(
        "은하 종류를 선택하세요",
        ["타원은하 (E0~E7)", "나선은하 (Sa~Sc, SBa~SBc)", "불규칙은하 (Irr)"]
    )

    if class_type == "타원은하 (E0~E7)":
        subtype = st.slider("세부형 (E0: 둥근 / E7: 납작)", 0, 7, 3)
        st.success(f"선택된 분류: E{subtype}")
    elif class_type == "나선은하 (Sa~Sc, SBa~SBc)":
        subtype = st.selectbox("세부형 선택", ["Sa", "Sb", "Sc", "SBa", "SBb", "SBc"])
        st.success(f"선택된 분류: {subtype}")
    else:
        st.success("선택된 분류: 불규칙은하 (Irr)")

    st.text_area("비고", placeholder="관측 소감이나 특징을 기록하세요.")
    st.button("결과 저장")
