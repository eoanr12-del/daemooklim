# 유튜브 썸네일 이미지 프롬프트 규칙

## 목표

creative-strategy.md Phase 5에서 참조하는 **프롬프트 작성 규칙**.
확정된 썸네일 이미지 컨셉을 AI 이미지 프롬프트로 변환할 때 이 규칙을 따른다.
사용자가 텍스트를 직접 추가하므로, **이미지에 텍스트를 절대 포함하지 않는다.**

---

## 채널별 썸네일 전략

`config/thumbnail-strategy.json`이 있으면 해당 설정을 따른다. **없으면 기본값 사용.**

---

## 프롬프트 생성

### 장수 & 스타일 배분

`thumbnail-strategy.json`의 `count`(장수)와 `art_styles`(스타일 목록)에 따라 배분한다.

**배분 공식:**
- 와일드카드 1장을 먼저 확보
- 나머지 = `count - 1`
- 나머지를 컨셉A/B × 스타일 수로 균등 배분

**예시:**

| count | art_styles | 배분 |
|-------|-----------|------|
| 5 | [photorealistic, anime] | A(실사, 애니메) + B(실사, 애니메) + 와일드 1 |
| 3 | [photorealistic] | A(실사) + B(실사) + 와일드 1 |
| 7 | [photorealistic, anime] | A(실사, 애니메) + B(실사, 애니메) + 와일드 3 |
| 5 | [photorealistic, 3d-render] | A(실사, 3D) + B(실사, 3D) + 와일드 1 |

**기본값** (thumbnail-strategy.json 없음): 5장, [photorealistic, anime]

> **핵심**: 컨셉 A와 B는 본질적으로 다른 비주얼 방향이어야 한다 (단순 구도/색감 변형 금지). 같은 컨셉 내에서 스타일 차이로 선택지를 제공한다.

### 프롬프트 작성 규칙

1. **영어로 작성**: AI 이미지 생성 모델에 최적화
2. **실존 인물 실명 포함**: 전략에 실존 인물이 포함된 경우, 프롬프트에 반드시 실명과 직함을 영문으로 표기한다. 예: `"Lee Jae-yong (Samsung Electronics chairman)"`, `"Jensen Huang (NVIDIA CEO)"`. 일반화("an Asian man in a suit")는 금지.
3. **비실존 인물 외모**: 특정 실존 인물이 아닌 일반 캐릭터/인물이 등장할 경우, `"attractive, appealing appearance, likeable face"` 등을 추가하여 호감형 외모로 생성한다. 실사 스타일이면 `"attractive young woman/man with a warm likeable face"`, 애니메 스타일이면 `"beautiful/handsome anime character with expressive eyes"` 형태로.
4. **3~5문장**: 구체적이고 생생하게, 하지만 과도하게 길지 않게
5. **고유명사 보존**: concept_ko의 브랜드명, 제품명, 고유명사는 영어 프롬프트에 반드시 그대로 보존한다. 예: "HBM4 칩" → "Samsung HBM4 memory chip" (단순 "semiconductor chip"으로 일반화 금지)
6. **스타일 명시**: 배분된 아트 스타일을 프롬프트 앞부분에 명시. 실사: `"photorealistic"`, `"cinematic"`. 애니메: `"anime-style illustration"`, `"vibrant anime art"`, `"stylized digital illustration"`. 커스텀 스타일이면 해당 스타일 키워드 사용.
7. **구도 명시**: 좌우 배치, 중앙 집중, 원근 등 구도를 구체적으로 서술
8. **모바일 주목성**: 피사체를 크고 명확하게 묘사하여 모바일 소형 썸네일에서도 한눈에 알아볼 수 있도록 한다
9. **국기·상징물 주의**: 일본 국기는 반드시 일반 국기(日章旗, 흰 바탕에 빨간 원)만 사용한다. 전범기(旭日旗, 방사형 광선)는 절대 금지. 프롬프트에 `"Japanese national flag (white flag with red circle)"` 형태로 명시하고, `"rising sun"`, `"rays"`, `"imperial"` 등 전범기를 연상시키는 표현을 사용하지 않는다.

---

## 채널 전략 반영 규칙

`thumbnail-strategy.json`의 각 필드에 따라 프롬프트 스타일이 달라진다. 없으면 기본값 적용.

### 색감 (`color_palette`)

| 값 | 프롬프트 키워드 | 기본값 |
|----|---------------|--------|
| `bright` | `"bright vibrant colors"`, `"clean white or light background"`, `"high-key lighting"`, `"vivid saturated tones"` | **기본값** |
| `dark` | `"dark cinematic atmosphere"`, `"deep shadows"`, `"dramatic contrast"`, `"moody lighting"` | |
| `pastel` | `"soft pastel colors"`, `"gentle warm tones"`, `"light airy atmosphere"`, `"muted saturation"` | |
| `neon` | `"neon glow"`, `"cyberpunk color palette"`, `"fluorescent accents"`, `"dark background with vivid neon highlights"` | |
| `monotone` | `"desaturated monochrome"`, `"black and white with single accent color"`, `"high contrast grayscale"` + brand.colors에서 포인트 컬러 적용 | |
| `auto` | 주제에 따라 위 중 가장 적합한 색감을 자체 판단 | |

### 감정톤 (`emotions`)

| 값 | 과장 수준 & 분위기 지시 |
|----|----------------------|
| `shock` | 과장 극대화. 인물: `"exaggerated expression"`, `"extreme close-up"`, `"oversized face"`. 물체: `"dramatically oversized"`, `"towering over"`. 목표 감정: 놀라움·충격 |
| `curiosity` | 중간 과장. 일부만 보여주기, `"partially revealed"`, `"mysterious composition"`, `"intriguing"`. 목표: 궁금증 |
| `tension` | 강한 대비. `"ominous atmosphere"`, `"cracks"`, `"fractures"`, `"dark shadows"`. 목표: 긴장감·위기 |
| `trust` | 과장 최소화. `"clean professional layout"`, `"organized composition"`, `"calm confident"`. 목표: 신뢰·전문성 |
| `warmth` | 부드러운 톤. `"warm lighting"`, `"soft focus"`, `"gentle expression"`, `"inviting atmosphere"`. 목표: 따뜻함·공감 |
| `humor` | 코믹한 과장. `"comically exaggerated"`, `"playful"`, `"bright cheerful"`, `"cartoon-like proportions"`. 목표: 재미·유머 |
| `premium` | 미니멀. `"elegant minimalist"`, `"luxurious"`, `"sophisticated"`, `"premium feel"`, `"gold accents"`. 목표: 고급스러움 |

> 2개 선택된 경우, 첫 번째를 주된 톤으로 사용하고 두 번째를 보조 뉘앙스로 반영.
> 기본값: `["shock", "curiosity"]`
> 징그럽거나 혐오를 유발하는 과장은 어떤 감정이든 금지.

### 텍스트 공간 (`text_space`)

| 값 | 구도 규칙 |
|----|----------|
| `bottom-half` | **상단 1/2에 핵심 피사체를 좌우 꽉 차게** 배치. **하단 1/2는 단순 배경만** — 인물 얼굴, 로고, 핵심 오브젝트 등 중요한 요소가 하단에 오면 안 됨. **(기본값)** |
| `full` | 전체 프레임을 이미지로 채움. 텍스트 공간 확보 불필요. 피사체를 프레임 전체에 배치. |
| `left-right` | 핵심 피사체를 한쪽(좌 또는 우)에 배치. 반대쪽은 단순 배경으로 텍스트 공간 확보. |

> **boilerplate 불포함**: 아래는 `generate_thumbnails.py`가 `text_space` 설정에 따라 자동 추가하므로 prompt_en에 포함하지 않는다:
> 1. 16:9 비율 (`wide 16:9 aspect ratio, YouTube thumbnail composition`)
> 2. 구도 규칙 (`text_space`에 해당하는 composition 지시문)
> 3. 텍스트 금지 (`no text, no letters, no words, no numbers, no watermark`)

### 인물 표현 (`face_style`)

| 값 | 인물 묘사 방식 |
|----|--------------|
| `exaggerated` | 과장된 표정 클로즈업. `"exaggerated expression"`, `"extreme close-up"`, `"oversized face filling the frame"` **(기본값)** |
| `natural` | 자연스러운 인물. 실제 비율, 사실적 표정. `"natural proportions"`, `"realistic expression"` |
| `silhouette` | 실루엣/뒷모습. `"dark silhouette"`, `"backlit figure"`, `"mysterious back view"` |
| `minimize` | 인물 최소화. 오브젝트/그래픽 중심. 인물이 꼭 필요한 경우에만 작게 배치. |
| `auto` | 주제에 따라 자체 판단. 인물이 핵심인 주제만 인물 포함. |

### 브랜드 (`brand`)

- **brand.colors**: 지정된 색상이 있으면, 프롬프트에 해당 색상을 포인트 컬러로 반영. 예: `brand.colors: ["#00C4B3"]` → `"mint-green accent color (#00C4B3)"`.
- **brand.mascot**: `true`이면, `config/assets/mascot/` 의 이미지를 참고하여 유사한 캐릭터를 프롬프트에 포함. 단, AI 이미지 생성에서 캐릭터 일관성은 제한적이므로 "참고" 수준.
- **brand.fixed_layout**: 고정 구도가 지정되어 있으면 해당 구도를 모든 프롬프트에 적용. 예: `"항상 좌측에 인물, 우측에 핵심 오브젝트"` → 모든 프롬프트에 이 배치 반영.

---

## 출력 형식

아래 JSON 형식으로 저장한다.

```json
{
  "meta": {
    "project": "{프로젝트명}",
    "titles": ["{추천 제목}", "{제목 후보 2}", "{제목 후보 3}"],
    "thumbnail_texts": ["{텍스트 세트 1}", "{텍스트 세트 2}", "{텍스트 세트 3}"],
    "image_concepts": {
      "A": "{컨셉 A 한줄 설명}",
      "B": "{컨셉 B 한줄 설명}"
    }
  },
  "thumbnails": [
    {
      "id": 1,
      "type": "concept-a-realistic",
      "concept_ko": "컨셉 A 실사. 배민 라이더가 무너지는 도시 앞에 서있는 시네마틱 장면.",
      "prompt_en": "Cinematic dramatic photograph of a Baemin delivery rider standing in front of a crumbling dark cityscape. The rider's mint-green uniform contrasts sharply against the shadowy backdrop with visible cracks spreading across buildings. Dramatic side lighting casts long shadows, creating a moody atmosphere of decline and crisis."
    },
    {
      "id": 2,
      "type": "concept-a-anime",
      "concept_ko": "컨셉 A 애니메. 같은 라이더+도시 붕괴를 애니메 스타일로 표현.",
      "prompt_en": "Vibrant anime-style illustration of a Baemin delivery rider standing before a dramatically crumbling cityscape. Bold ink outlines and cel-shaded lighting emphasize the contrast between the rider's mint-green uniform and the dark, fractured buildings behind. Intense dramatic atmosphere with exaggerated perspective and vivid color contrast."
    }
  ]
}
```

### 필드 설명

| 필드 | 설명 |
|------|------|
| `meta.titles` | 제목 후보 3개 배열. 첫 번째가 추천안 (concept.md "제목 후보" 3개 그대로) |
| `id` | 1~N 번호 (thumbnail-strategy.json의 count에 따라) |
| `type` | `concept-{a|b}-{style}` 또는 `wildcard`. 스타일명은 art_styles에서 결정 |
| `concept_ko` | 한국어로 이 이미지가 무엇을 보여주는지 1~2문장 설명 |
| `prompt_en` | AI 이미지 생성용 영어 프롬프트 (3~5문장, boilerplate 미포함) |
