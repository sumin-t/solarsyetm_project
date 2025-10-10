# -*- coding: utf-8 -*-
"""
우주 관광 여행 상품 이미지 생성기 (DALL·E 3 · 단일 화면)
- 행성의 과학적 사실 + 사용자의 아이디어(프롬프트) 반영
- 주제: 우주 관광 여행자들이 실제로 여행하는 모습을 표현
- 출력: 리플릿(상품 홍보지)에 사용할 사진
"""

from __future__ import annotations
import io
import time
import base64
from typing import Tuple, Dict, List
import requests
from PIL import Image, ImageDraw
import streamlit as st

# -----------------------------
# 설정 및 데이터
# -----------------------------
PLANETS = [
    {"id": "mercury", "kr": "수성", "en": "Mercury", "emoji": "🪨", "tip": "회색 바위 표면, 얇은 대기"},
    {"id": "venus",   "kr": "금성", "en": "Venus",   "emoji": "🌕", "tip": "두꺼운 황산 구름, 황금빛"},
    {"id": "mars",    "kr": "화성", "en": "Mars",    "emoji": "🔴", "tip": "붉은 사막, 거대한 화산"},
    {"id": "jupiter", "kr": "목성", "en": "Jupiter", "emoji": "🌀", "tip": "적반점, 가스 거대 행성"},
    {"id": "saturn",  "kr": "토성", "en": "Saturn",  "emoji": "💍", "tip": "아름다운 고리"},
    {"id": "uranus",  "kr": "천왕성", "en": "Uranus",  "emoji": "🧊", "tip": "청록빛, 옆으로 누운 자전축"},
    {"id": "neptune", "kr": "해왕성", "en": "Neptune", "emoji": "🌊", "tip": "짙은 파랑, 강한 바람"},
]
PLANET_BY_KR: Dict[str, Dict] = {p["kr"]: p for p in PLANETS}

SCIENCE_FACTS: Dict[str, List[str]] = {
    "수성": ["암석형 행성, 회색 바위와 충돌 크레이터가 많음", "대기가 거의 없음", "극지에 얼음 존재 가능성"],
    "금성": ["두꺼운 황산 구름층, 표면 직접 관측 불가", "온실효과로 표면 온도가 매우 높음", "하늘은 황금빛, 지표는 용암평원"],
    "화성": ["붉은 산화철 토양, 얇은 대기", "올림푸스 산, 거대한 협곡 존재", "극지방에 얼음 모자"],
    "목성": ["가스형 거대 행성, 적반점 존재", "강한 대기 흐름과 띠무늬 구름", "고체 표면 없음"],
    "토성": ["넓은 얼음 고리", "가스형 행성, 연한 황갈색 띠무늬", "여러 위성(타이탄 등) 존재"],
    "천왕성": ["청록빛, 옆으로 누운 자전축", "메탄으로 인해 푸른색 계열", "차가운 가스/얼음 행성"],
    "해왕성": ["짙은 파란색, 강한 폭풍과 바람", "어두운 반점 존재", "가스/얼음 혼합 구조"],
}

IMG_SIZE = "1024x1024"
MODEL_NAME = "dall-e-3"

# -----------------------------
# 유틸 함수
# -----------------------------
def pil_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()

def generate_placeholder_image(title: str, subtitle: str, size: str) -> Image.Image:
    from random import randint
    w, h = 1024, 1024
    img = Image.new("RGB", (w, h), (10, 15, 30))
    d = ImageDraw.Draw(img)
    for _ in range(150):
        x, y = randint(0, w-1), randint(0, h-1)
        d.ellipse((x, y, x+2, y+2), fill=(255, 255, 255))
    d.text((30, 40), title, fill=(240, 240, 240))
    d.text((30, 80), subtitle[:80], fill=(200, 200, 200))
    return img

# -----------------------------
# ✅ 수정된 핵심 함수
# -----------------------------
def call_openai_image(api_key: str, prompt: str, size: str, model: str) -> Image.Image:
    """DALL·E 3 호출 (b64_json 고정 + URL 폴백 지원)"""
    url = "https://api.openai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "response_format": "b64_json",  # ★ base64 응답으로 강제
    }

    r = requests.post(url, headers=headers, json=payload, timeout=90)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        try:
            msg = r.json().get("error", {}).get("message", r.text)
        except Exception:
            msg = r.text
        raise RuntimeError(f"HTTP {r.status_code}: {msg}") from None

    j = r.json()
    data0 = (j.get("data") or [{}])[0]

    b64 = data0.get("b64_json")
    if b64:
        return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")

    img_url = data0.get("url")
    if img_url:
        resp = requests.get(img_url, timeout=90)
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGB")

    raise RuntimeError("응답에 이미지 데이터가 없습니다. (b64_json/url 모두 없음)")

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="우주 관광 여행 상품 이미지 생성기", page_icon="🚀", layout="wide")
st.title("🚀 우주 관광 여행 상품 이미지 생성기")
st.caption("종암중학교 · 과학 수행평가용 · 리플릿용 사진 (DALL·E 3)")

if "selected_planet_kr" not in st.session_state:
    st.session_state.selected_planet_kr = "화성"
if "generated_image" not in st.session_state:
    st.session_state.generated_image = None

# ---- 1) 행성 선택 ----
st.markdown("### 1) 행성 선택 (지구 제외)")
planet_labels = [f"{p['kr']} ({p['en']})" for p in PLANETS]
label_to_planet = {f"{p['kr']} ({p['en']})": p for p in PLANETS}
current_label = f"{st.session_state.selected_planet_kr} ({PLANET_BY_KR[st.session_state.selected_planet_kr]['en']})"
if current_label not in planet_labels:
    current_label = planet_labels[0]
selected_label = st.selectbox("행성 선택", options=planet_labels, index=planet_labels.index(current_label))
selected_planet = label_to_planet[selected_label]
st.session_state.selected_planet_kr = selected_planet["kr"]
st.caption(f"힌트: {selected_planet['kr']} — {selected_planet['tip']}")

# ---- 2) 프롬프트 작성 ----
st.markdown("### 2) 프롬프트 작성 (필수)")
st.write("예시) **'화성 협곡 위 유리돔 리조트에서 우주 관광객들이 로버 투어를 즐기는 장면'**")
user_prompt = st.text_area(
    "홍보용 이미지에 포함하고 싶은 요소를 입력하세요 (예: 리조트, 셔틀, 관광객, 탐사 로버, 안전 브리핑 등)",
    value="관광객, 리조트, 로버 투어, 전망 포인트, 셔틀 착륙, 안전 복장",
    height=120,
)

# ---- 3) API Key ----
st.markdown("### 3) OpenAI API Key (필수, 저장되지 않음)")
api_key = st.text_input("OpenAI API Key", type="password")

# ---- 최종 프롬프트 ----
planet = PLANET_BY_KR[st.session_state.selected_planet_kr]
facts_text = ", ".join(SCIENCE_FACTS.get(planet["kr"], []))
final_prompt = (
    f"'{planet['kr']} ({planet['en']})' 행성의 과학적 사실을 반영한 사실적 사진.\n"
    f"내용: 우주 관광 여행 상품 홍보용 이미지로, 관광객들이 실제로 여행을 즐기고 있는 장면을 표현.\n"
    f"과학적 특징: {facts_text}.\n"
    f"사용자 아이디어: {user_prompt}.\n"
    f"텍스트나 로고 없이, 리플릿(상품 홍보지)에 바로 사용할 수 있는 고해상도 사진 스타일로."
)

with st.expander("자동으로 구성된 최종 프롬프트 보기"):
    st.code(final_prompt)

# ---- 4) 이미지 생성 / 미리보기 ----
col_left, col_right = st.columns([0.48, 0.52])
with col_left:
    st.markdown("### 4) 이미지 생성")
    make = st.button("✨ 이미지 생성", use_container_width=True, type="primary")
    if make:
        if not api_key.strip():
            st.warning("API Key를 입력하세요.")
        elif not user_prompt.strip():
            st.warning("프롬프트를 입력하세요.")
        else:
            try:
                st.session_state.generated_image = call_openai_image(api_key, final_prompt, IMG_SIZE, MODEL_NAME)
                st.success("이미지 생성 완료!")
            except Exception as e:
                st.session_state.generated_image = generate_placeholder_image(
                    f"{planet['kr']} ({planet['en']}) 우주 관광", str(e), IMG_SIZE
                )
                st.error(f"API 오류 발생: {e}")

with col_right:
    st.markdown("### 미리보기")
    if isinstance(st.session_state.generated_image, Image.Image):
        st.image(st.session_state.generated_image, use_column_width=True)
    else:
        st.info("왼쪽에서 '이미지 생성'을 먼저 눌러 주세요.")

# ---- 다운로드 ----
st.markdown("### 이미지 저장")
if isinstance(st.session_state.generated_image, Image.Image):
    data = pil_to_bytes(st.session_state.generated_image)
    filename = f"{planet['id']}_{int(time.time())}.png"
    st.download_button("📥 PNG로 다운로드", data=data, file_name=filename, mime="image/png")
else:
    st.button("📥 PNG로 다운로드", disabled=True)

# ---- 푸터 ----
st.divider()
st.markdown(
    f"<div style='text-align:center; color:#94a3b8'>© {time.strftime('%Y')} 종암중학교 · 교육용 데모 · <b>이수민t 제작</b></div>",
    unsafe_allow_html=True,
)
