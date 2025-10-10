# -*- coding: utf-8 -*-
"""
태양계 행성 여행 상품 이미지 생성기 (Streamlit · 탭 UI)
요구 반영
- 탭 구성: (1) 행성 선택, (2) 프롬프트 작성
- 요소: 행성 선택(단일 선택), 프롬프트(필수, 예시 1개), API Key 입력, 이미지 생성, 이미지 저장
- 매 사용 시 API Key 입력(저장하지 않음)
- 하단 '이수민t 제작' 표기

실행 방법
    pip install streamlit pillow requests
    streamlit run app.py

주의
- 본 예시는 OpenAI 이미지 생성 API(images/generations)를 사용합니다.
- 학생 배포 시에는 프론트에서 키를 직접 받지 말고, 선생님 전용 서버 프록시를 사용하는 것이 안전합니다.
"""

from __future__ import annotations
import io
import time
import base64
from typing import Tuple, Dict

import requests
from PIL import Image, ImageDraw
import streamlit as st

# -----------------------------
# 설정 및 데이터
# -----------------------------
PLANETS = [
    {"id": "mercury", "kr": "수성", "en": "Mercury", "emoji": "🪨", "tip": "회색 바위 표면, 얇은 대기"},
    {"id": "venus",   "kr": "금성", "en": "Venus",   "emoji": "🌕", "tip": "두꺼운 황산 구름, 황금빛"},
    {"id": "earth",   "kr": "지구", "en": "Earth",   "emoji": "🌍", "tip": "푸른 바다, 하얀 구름"},
    {"id": "mars",    "kr": "화성", "en": "Mars",    "emoji": "🔴", "tip": "붉은 사막, 거대한 화산"},
    {"id": "jupiter", "kr": "목성", "en": "Jupiter", "emoji": "🌀", "tip": "적반점, 가스 거대 행성"},
    {"id": "saturn",  "kr": "토성", "en": "Saturn",  "emoji": "💍", "tip": "아름다운 고리"},
    {"id": "uranus",  "kr": "천왕성", "en": "Uranus",  "emoji": "🧊", "tip": "청록빛, 옆으로 누운 자전축"},
    {"id": "neptune", "kr": "해왕성", "en": "Neptune", "emoji": "🌊", "tip": "짙은 파랑, 강한 바람"},
]
PLANET_BY_KR: Dict[str, Dict] = {p["kr"]: p for p in PLANETS}

IMG_SIZE = "1024x1024"   # 고정
MODEL_NAME = "gpt-image-1"

# -----------------------------
# 유틸 함수
# -----------------------------
def parse_size(size: str) -> Tuple[int, int]:
    try:
        w, h = size.lower().split("x")
        return int(w), int(h)
    except Exception:
        return 1024, 1024

def pil_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()

def generate_placeholder_image(title: str, subtitle: str, size: str) -> Image.Image:
    """오프라인 혹은 오류 시 표시할 간단한 플레이스홀더 이미지"""
    w, h = parse_size(size)
    img = Image.new("RGB", (w, h), (6, 10, 25))
    d = ImageDraw.Draw(img)
    import random
    for _ in range(max(60, (w * h) // 30000)):
        x, y = random.randint(0, w - 1), random.randint(0, h - 1)
        r = random.randint(1, 2)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255))
    R = int(min(w, h) * 0.23)
    cx, cy = int(w * 0.38), int(h * 0.62)
    d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=(40, 44, 68))
    d.text((int(w * 0.08), int(h * 0.10)), title, fill=(230, 230, 230))
    # 간단 줄바꿈
    wrap = max(18, w // 26)
    words = subtitle.split(" ")
    line, yy = "", int(h * 0.16)
    for wd in words:
        test = (line + wd + " ").strip()
        if len(test) > wrap:
            d.text((int(w * 0.08), yy), line, fill=(200, 200, 200))
            line = wd + " "
            yy += int(w * 0.028)
        else:
            line = test + " "
    if line:
        d.text((int(w * 0.08), yy), line, fill=(200, 200, 200))
    return img

def call_openai_image(api_key: str, prompt: str, size: str, model: str) -> Image.Image:
    """OpenAI 이미지 생성 API 호출"""
    url = "https://api.openai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"prompt": prompt, "n": 1, "size": size, "model": model}
    r = requests.post(url, headers=headers, json=payload, timeout=90)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        # 에러 전문도 같이 보여주면 원인 파악에 도움
        raise RuntimeError(f"HTTP {r.status_code}: {r.text}") from None
    j = r.json()
    b64 = (j.get("data") or [{}])[0].get("b64_json")
    if not b64:
        raise RuntimeError("응답에 이미지 데이터가 없습니다. 모델/권한을 확인하세요.")
    data = base64.b64decode(b64)
    return Image.open(io.BytesIO(data)).convert("RGB")

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="태양계 행성 여행 이미지 생성기", page_icon="🚀", layout="wide")
st.title("🚀 태양계 행성 여행 상품 이미지 생성기")
st.caption("종암중학교 · 과학 수행평가용 · 탭 버전")

# 상태
if "selected_planet_kr" not in st.session_state:
    st.session_state.selected_planet_kr = "화성"  # 기본: 화성
if "generated_image" not in st.session_state:
    st.session_state.generated_image = None

# --- 탭: 1) 행성 선택 / 2) 프롬프트 작성 ---
tab_planet, tab_prompt = st.tabs(["1) 행성 선택", "2) 프롬프트 작성"])

with tab_planet:
    st.markdown("### 태양계 행성을 1개 선택하세요")
    planet_labels = [f"{p['emoji']} {p['kr']} ({p['en']})" for p in PLANETS]
    planet_kr_options = [p["kr"] for p in PLANETS]

    # kr만 라디오로 저장(단일 선택)
    chosen_kr = st.radio(
        "행성",
        options=planet_kr_options,
        index=planet_kr_options.index(st.session_state.selected_planet_kr),
        horizontal=True,
        help="한 번에 한 행성만 선택됩니다.",
    )
    st.session_state.selected_planet_kr = chosen_kr

    # 선택 행성 힌트
    p = PLANET_BY_KR[st.session_state.selected_planet_kr]
    st.caption(f"힌트: {p['kr']} — {p['tip']}")

with tab_prompt:
    st.markdown("### 프롬프트를 작성하세요 (필수)")
    st.write("예시) **'화성의 거대한 협곡을 배경으로 한 친환경 관광 상품, 안전 장비, 교육적 안내 표지, 학생 체험 프로그램'**")
    # 스타일 지시는 넣지 않기(요청사항)
    user_prompt = st.text_area(
        "프롬프트 (필수 입력)",
        value="미래형 우주 리조트, 학생 여행단, 안전한 이동수단, 과학 체험 프로그램",
        height=120,
        placeholder="원하는 요소를 쉼표로 나열해 주세요. (예: 안전한 이동수단, 거주 시설, 관광 포인트...)",
    )

# API Key (매번 입력)
st.markdown("### OpenAI API Key (필수, 세션에 저장하지 않습니다)")
api_key = st.text_input("OpenAI API Key", type="password", help="요청 시에만 사용되며 세션에 저장하지 않습니다.")

# 최종 프롬프트(스타일 지시 제거, 필수 정보만)
planet = PLANET_BY_KR[st.session_state.selected_planet_kr]
final_prompt = "\n".join([
    f"중학생 과학 프로젝트를 위한 홍보용 이미지: '{planet['kr']} ({planet['en']})' 여행 상품.",
    f"행성 특징: {planet['tip']}.",
    "구성 요소: 우주선, 거주 시설, 관광 포인트, 소형 안내문이 들어갈 빈 영역(실제 글자는 넣지 않음).",
    f"학생 아이디어: {user_prompt}",
])

with st.expander("자동으로 구성된 최종 프롬프트 보기"):
    st.code(final_prompt)

# 이미지 생성 & 미리보기
left, right = st.columns([0.48, 0.52], vertical_alignment="top")
with left:
    st.markdown("### 이미지 생성")
    make = st.button("✨ 이미지 생성", use_container_width=True, type="primary")
    if make:
        st.session_state.generated_image = None
        if not user_prompt.strip():
            st.warning("프롬프트는 필수입니다. 내용을 입력해 주세요.")
        elif not api_key.strip():
            st.warning("API Key를 입력해 주세요.")
        else:
            try:
                st.session_state.generated_image = call_openai_image(api_key, final_prompt, IMG_SIZE, MODEL_NAME)
                st.success("이미지 생성 완료!")
            except Exception as e:
                # 실패 시 플레이스홀더
                st.session_state.generated_image = generate_placeholder_image(
                    f"{planet['kr']} ({planet['en']}) 여행 홍보 이미지",
                    f"프롬프트: {user_prompt}",
                    IMG_SIZE,
                )
                st.error(f"API 오류로 플레이스홀더 이미지를 표시합니다.\n\n상세: {e}")

with right:
    st.markdown("### 미리보기")
    if isinstance(st.session_state.generated_image, Image.Image):
        st.image(st.session_state.generated_image, use_column_width=True)
    else:
        st.info("왼쪽에서 '이미지 생성'을 먼저 눌러 주세요.")

# 다운로드
st.markdown("### 이미지 저장")
if isinstance(st.session_state.generated_image, Image.Image):
    data = pil_to_bytes(st.session_state.generated_image, fmt="PNG")
    filename = f"{planet['id']}_{int(time.time())}.png"
    st.download_button("📥 PNG로 다운로드", data=data, file_name=filename, mime="image/png")
else:
    st.button("📥 PNG로 다운로드", disabled=True)

# 푸터
st.divider()
st.markdown(
    "<div style='text-align:center; color:#94a3b8'>© {} 종암중학교 · 교육용 데모 · <b>이수민t 제작</b></div>".format(time.strftime("%Y")),
    unsafe_allow_html=True,
)
