import os
import csv
import gc
import re
import logging
import pandas as pd
import numpy as np
from typing import List
import spacy
from langdetect import detect
from deep_translator import GoogleTranslator
from pdf_extractor import PDFExtractor

# ============================================================
# CONFIG
# ============================================================
HEALTH_TERMS_FILE = "./keywords/health_terms.txt"
ADAPTATION_TERMS_FILE = "./keywords/adaptation_terms.txt"
HEALTH_AUTHORITY_FILE = "./keywords/health_authority_terms.txt"

INPUT_DATA = "./data/euro_legis_df.csv"
OUTPUT_FILE = "./outputs/dataframes/health_annotations.csv"
LOG_FILE = "./outputs/dataframes/pipeline_log.txt"

WINDOW_SIZE = 100
MIN_OVERLAP_WORDS = 20
CHUNK_SIZE = 5000

OUTPUT_COLUMNS = [
    "Doc ID",
    "Country",
    "Year",
    "Response",
    "Health relevance (1/0)",
    "Health adaptation mandate (1/0)",
    "Institutional health role (1/0)",
    "Matched health keywords",
    "Health keyword categories",
    "Notes"
]

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ============================================================
# NLP
# ============================================================
nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
nlp.add_pipe("sentencizer")

# ============================================================
# LOAD KEYWORDS
# ============================================================
def load_keyword_set(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

# ============================================================
# HEALTH TERM → CATEGORY MAPPING
# ============================================================
health_term_categories = {

# --- General health & services ---
"health": "general_health",
"well-being": "general_health",
"wellbeing": "general_health",
"medical": "general_health",
"healthcare": "general_health",
"health care": "general_health",
"health service": "general_health",
"health clinic": "general_health",
"hospital": "general_health",
"hospitalisation": "general_health",
"doctor": "general_health",
"gp": "general_health",
"health emergency": "general_health",
"emergency": "general_health",

# --- Mortality & morbidity ---
"mortality": "mortality_morbidity",
"morbidity": "mortality_morbidity",
"daly": "mortality_morbidity",
"death": "mortality_morbidity",
"deaths": "mortality_morbidity",
"loss of life": "mortality_morbidity",
"loss of lives": "mortality_morbidity",
"human life": "mortality_morbidity",

# --- Injury & physical harm ---
"injury": "injury_trauma",
"injuries": "injury_trauma",
"accident": "injury_trauma",
"traumatic injury": "injury_trauma",
"fatigue": "injury_trauma",

# --- General disease terms ---
"disease": "communicable_disease",
"diseases": "communicable_disease",
"ill": "communicable_disease",
"illness": "communicable_disease",
"illnesses": "communicable_disease",
"syndrome": "communicable_disease",
"infection": "communicable_disease",
"infections": "communicable_disease",
"pathogen": "pathogens_microbiology",
"pathogens": "pathogens_microbiology",
"epidemiology": "communicable_disease",
"epidemic": "communicable_disease",
"epidemics": "communicable_disease",
"pandemic": "communicable_disease",
"pandemics": "communicable_disease",

# --- Communicable diseases ---
"malaria": "communicable_disease",
"diarrhoea": "communicable_disease",
"diarrhea": "communicable_disease",
"diarrheal disease": "communicable_disease",
"diarrhoeal disease": "communicable_disease",
"cholera": "communicable_disease",
"typhoid": "communicable_disease",
"dysentery": "communicable_disease",
"leptospirosis": "communicable_disease",
"polio": "communicable_disease",
"measles": "communicable_disease",
"sars": "communicable_disease",
"severe acute respiratory syndrome": "communicable_disease",
"tuberculosis": "communicable_disease",
"tb": "communicable_disease",
"influenza": "communicable_disease",
"flu": "communicable_disease",
"pneumonia": "communicable_disease",
"respiratory tract infection": "communicable_disease",
"covid-19": "communicable_disease",
"covid": "communicable_disease",
"coronavirus disease 2019": "communicable_disease",
"coronavirus": "communicable_disease",
"ebola": "communicable_disease",
"hepatitis": "communicable_disease",
"hiv": "communicable_disease",
"human immunodeficiency virus": "communicable_disease",
"aids": "communicable_disease",
"acquired immunodeficiency syndrome": "communicable_disease",
"sexually transmitted infection": "communicable_disease",
"sexually transmitted infections": "communicable_disease",
"sexually transmitted disease": "communicable_disease",
"fever": "communicable_disease",
"feverish": "communicable_disease",
"sepsis": "communicable_disease",

# --- Non-communicable diseases ---
"ncd": "non_communicable_disease",
"ncds": "non_communicable_disease",
"non-communicable disease": "non_communicable_disease",
"non-communicable diseases": "non_communicable_disease",
"cardiovascular disease": "non_communicable_disease",
"cvd": "non_communicable_disease",
"heart disease": "non_communicable_disease",
"heart attack": "non_communicable_disease",
"heart attacks": "non_communicable_disease",
"heart failure": "non_communicable_disease",
"coronary heart disease": "non_communicable_disease",
"chd": "non_communicable_disease",
"ischaemic heart disease": "non_communicable_disease",
"cerebrovascular disease": "non_communicable_disease",
"stroke": "non_communicable_disease",
"peripheral arterial disease": "non_communicable_disease",
"congenital heart disease": "non_communicable_disease",
"rheumatic heart disease": "non_communicable_disease",
"deep vein thrombosis": "non_communicable_disease",
"pulmonary embolism": "non_communicable_disease",
"hypertension": "non_communicable_disease",
"blood pressure": "non_communicable_disease",
"diabetes": "non_communicable_disease",
"chronic kidney disease": "non_communicable_disease",
"ckd": "non_communicable_disease",
"renal disease": "non_communicable_disease",
"kidney disease": "non_communicable_disease",
"cancer": "non_communicable_disease",
"chronic respiratory disease": "non_communicable_disease",
"chronic obstructive pulmonary disease": "non_communicable_disease",
"copd": "non_communicable_disease",
"chronic bronchitis": "non_communicable_disease",
"emphysema": "non_communicable_disease",
"asthma": "non_communicable_disease",
"bronchial asthma": "non_communicable_disease",
"allergic asthma": "non_communicable_disease",
"respiratory illness": "non_communicable_disease",
"respiratory conditions": "non_communicable_disease",
"respiratory": "non_communicable_disease",
"lung disease": "non_communicable_disease",
"pulmonary disease": "non_communicable_disease",
"bronchitis": "non_communicable_disease",
"rhinitis": "non_communicable_disease",
"hay fever": "non_communicable_disease",
"wheezing": "non_communicable_disease",
"allergies": "non_communicable_disease",
"allergens": "non_communicable_disease",
"immune system": "non_communicable_disease",

# --- Vector-borne & zoonotic ---
"vector-borne disease": "vector_borne_zoonotic",
"vector-borne diseases": "vector_borne_zoonotic",
"zoonoses": "vector_borne_zoonotic",
"zoonotic disease": "vector_borne_zoonotic",
"dengue": "vector_borne_zoonotic",
"chikungunya": "vector_borne_zoonotic",
"zika": "vector_borne_zoonotic",
"yellow fever": "vector_borne_zoonotic",
"west nile fever": "vector_borne_zoonotic",
"japanese encephalitis": "vector_borne_zoonotic",
"tick-borne encephalitis": "vector_borne_zoonotic",
"lyme disease": "vector_borne_zoonotic",
"borreliosis": "vector_borne_zoonotic",
"plague": "vector_borne_zoonotic",
"onchocerciasis": "vector_borne_zoonotic",
"river blindness": "vector_borne_zoonotic",
"lymphatic filariasis": "vector_borne_zoonotic",
"sleeping sickness": "vector_borne_zoonotic",
"trypanosomiasis": "vector_borne_zoonotic",
"american trypanosomiasis": "vector_borne_zoonotic",
"chagas disease": "vector_borne_zoonotic",
"ross river fever": "vector_borne_zoonotic",
"ross river virus": "vector_borne_zoonotic",
"barmah forest virus": "vector_borne_zoonotic",
"leishmaniasis": "vector_borne_zoonotic",
"schistosomiasis": "vector_borne_zoonotic",
"bilharziasis": "vector_borne_zoonotic",
"tungiasis": "vector_borne_zoonotic",

# --- Pathogens & toxins ---
"bacteria": "pathogens_microbiology",
"virus": "pathogens_microbiology",
"viral infection": "pathogens_microbiology",
"parasite": "pathogens_microbiology",
"protozoa": "pathogens_microbiology",
"prion": "pathogens_microbiology",
"toxins": "pathogens_microbiology",

# --- Food & waterborne ---
"salmonella": "food_waterborne",
"salmonellosis": "food_waterborne",
"campylobacter": "food_waterborne",
"campylobacteriosis": "food_waterborne",
"shigella": "food_waterborne",
"shigellosis": "food_waterborne",
"giardia": "food_waterborne",
"giardiasis": "food_waterborne",
"cryptosporidium": "food_waterborne",
"cryptosporidiosis": "food_waterborne",
"legionella": "food_waterborne",
"legionellosis": "food_waterborne",
"vibrio bacteria": "food_waterborne",
"food-borne disease": "food_waterborne",
"food-borne diseases": "food_waterborne",
"food-borne pathogens": "food_waterborne",
"waterborne disease": "food_waterborne",
"waterborne diseases": "food_waterborne",
"aflatoxin": "food_waterborne",
"mycotoxins": "food_waterborne",
"arsenic": "food_waterborne",
"botulism": "food_waterborne",
"ciguatera": "food_waterborne",
"poisoning": "food_waterborne",

# --- Nutrition ---
"nutrition": "nutrition",
"malnutrition": "nutrition",
"malnourishment": "nutrition",
"undernutrition": "nutrition",
"undernourished": "nutrition",
"stunting": "nutrition",
"wasting": "nutrition",
"underweight": "nutrition",
"overweight": "nutrition",
"obesity": "nutrition",
"hunger": "nutrition",
"anthropometry": "nutrition",
"micronutrient": "nutrition",
"micronutrient deficiency": "nutrition",
"micronutrient excess": "nutrition",
"anaemia": "nutrition",
"anemia": "nutrition",

# --- Maternal & child ---
"low birth weight": "maternal_child_health",
"lbw": "maternal_child_health",
"maternal health": "maternal_child_health",
"pregnancy": "maternal_child_health",
"pregnant": "maternal_child_health",
"gestation": "maternal_child_health",
"preterm birth": "maternal_child_health",
"stillbirth": "maternal_child_health",
"birth weight": "maternal_child_health",
"pre-eclampsia": "maternal_child_health",
"preeclampsia": "maternal_child_health",
"placenta": "maternal_child_health",
"oligohydramnios": "maternal_child_health",
"haemorrhage": "maternal_child_health",
"hemorrhage": "maternal_child_health",

# --- Environmental & climate ---
"air pollution": "environmental_health",
"thermal stress": "environmental_health",
"heat-related illness": "environmental_health",
"heat-related illnesses": "environmental_health",
"heat stress": "environmental_health",
"heat exhaustion": "environmental_health",
"heat cramp": "environmental_health",
"heat stroke": "environmental_health",
"hyperthermia": "environmental_health",
"hypothermia": "environmental_health",
"extreme heat": "environmental_health",
"heatwave": "environmental_health",
"high temperature": "environmental_health",
"flood": "environmental_health",
"drought": "environmental_health",
"wildfire": "environmental_health",
"bushfire": "environmental_health",
"bushfires": "environmental_health",
"algal bloom": "environmental_health",

# --- Mental health ---
"mental health": "mental_health",
"mental": "mental_health",
"mental illness": "mental_health",
"mental disorder": "mental_health",
"mental disorders": "mental_health",
"mental health condition": "mental_health",
"mental health disorder": "mental_health",
"mental health service": "mental_health",
"mental suffering": "mental_health",
"depression": "mental_health",
"depressed": "mental_health",
"depressive disorder": "mental_health",
"anxiety": "mental_health",
"anxious": "mental_health",
"phobia": "mental_health",
"suicide": "mental_health",
"suicidal": "mental_health",
"stress": "mental_health",
"stressful": "mental_health",
"psychological stress": "mental_health",
"psychological": "mental_health",
"psychosocial": "mental_health",
"psychiatric": "mental_health",
"psychiatric hospital": "mental_health",
"trauma": "mental_health",
"traumatic": "mental_health",
"post-traumatic stress": "mental_health",
"post-traumatic stress disorder": "mental_health",
"ptsd": "mental_health",
"grief": "mental_health",
"grieving": "mental_health",
"sadness": "mental_health",
"anger": "mental_health",
"despair": "mental_health",
"distress": "mental_health",
"distressed": "mental_health",
"cognitive impairment": "mental_health",
"cognitive disorder": "mental_health",
"cognitive deficits": "mental_health",
"impaired functioning": "mental_health",
"loss of concentration": "mental_health",
"insomnia": "mental_health",
"sleep disorder": "mental_health",
"sleep disruption": "mental_health",
"sleeplessness": "mental_health",
"eco-anxiety": "mental_health",
"solastalgia": "mental_health",
"ecological grief": "mental_health",
"eco-grief": "mental_health",

# --- Substance use ---
"substance use": "substance_use",
"substance abuse": "substance_use",
"drug use": "substance_use",
"alcohol": "substance_use",
"alcoholism": "substance_use",
}


# ============================================================
# LEGAL OBLIGATION + NEGATION
# ============================================================
OBLIGATION_REGEX = re.compile(
    r"\b(shall|must|is required to|are required to|shall ensure|must ensure|shall establish|"
    r"shall implement|shall develop|shall provide|shall adopt|shall include|obliged to|"
    r"mandatory|mandated|compulsory|duty to|responsible for ensuring|binding|"
    r"statutory requirement|legal obligation|enforceable)\b",
    re.IGNORECASE
)

NEGATION_REGEX = re.compile(
    r"\b(shall not|must not|not required to|no obligation to)\b",
    re.IGNORECASE
)

def contains_any(text: str, keywords: List[str]) -> bool:
    text_lower = text.lower()
    return any(k.lower() in text_lower for k in keywords)

def has_obligation(text: str) -> bool:
    if NEGATION_REGEX.search(text):
        return False
    return bool(OBLIGATION_REGEX.search(text))

# ============================================================
# TRANSLATION CACHE
# ============================================================
translation_cache = {}
def detect_and_translate(text: str, chunk_size: int = 4000) -> str:
    try:
        key = hash(text)
        if key in translation_cache:
            return translation_cache[key]

        lang = detect(text[:1000])
        if lang == "en":
            translation_cache[key] = text
            return text

        translator = GoogleTranslator(source=lang, target="en")
        translated_chunks = []
        start = 0
        while start < len(text):
            chunk = text[start:start+chunk_size]
            translated_chunks.append(translator.translate(chunk))
            start += chunk_size

        translated_text = " ".join(translated_chunks)
        translation_cache[key] = translated_text
        return translated_text
    except Exception as e:
        logging.warning(f"Translation failed: {e}")
        return text

# ============================================================
# WINDOW EXTRACTION
# ============================================================
def extract_relevant_windows(text: str, health_terms: List[str],
                             window_size: int = WINDOW_SIZE,
                             min_overlap: int = MIN_OVERLAP_WORDS) -> str:
    text = re.sub(r"\s+", " ", text)
    words = text.split()
    n = len(words)
    positions = [i for i, w in enumerate(words)
                 for k in health_terms if k.lower() in w.lower()]
    if not positions:
        return ""
    windows = [(max(0, p - window_size), min(n, p + window_size)) for p in positions]
    windows.sort()
    merged = [windows[0]]
    for start, end in windows[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end - min_overlap:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return "\n\n".join(" ".join(words[s:e]) for s, e in merged)

# ============================================================
# HEALTH TERM EXTRACTION & CATEGORY MAPPING
# ============================================================
def extract_health_keywords(text, canonical_keywords, chunk_size=4000):
    """
    Efficient extraction of health keywords from text.
    Handles non-English text via translation, set-based keyword matching, 
    and avoids per-chunk keyword loops.
    """
    if not text or not isinstance(text, str):
        return ""

    # --- Pre-clean the text once ---
    text_clean = re.sub(r"\[image\]|\[.*?\]", " ", text)
    text_clean = re.sub(r"[^\x00-\x7F]+", " ", text_clean)
    text_clean = re.sub(r"\s+", " ", text_clean).strip()
    if not text_clean:
        return ""

    # --- Language detection & translation ---
    try:
        lang = detect(text_clean[:1000])
        if lang != "en":
            translated_chunks = []
            for start in range(0, len(text_clean), chunk_size):
                chunk = text_clean[start:start + chunk_size]
                translated_chunks.append(GoogleTranslator(source=lang, target="en").translate(chunk))
            text_clean = " ".join(translated_chunks)
    except Exception as e:
        # fallback to original text if detection/translation fails
        pass

    # --- Fast keyword matching using set intersection ---
    text_words = set(re.findall(r'\w+', text_clean.lower()))
    keyword_set = set(kw.lower() for kw in canonical_keywords)
    found_keywords = text_words.intersection(keyword_set)

    return ";".join(sorted(found_keywords))


def map_terms_to_categories(term_string, mapping_dict):
    if not term_string or not isinstance(term_string, str):
        return ""
    terms = [t.strip().lower() for t in term_string.split(";") if t.strip()]
    categories = {mapping_dict.get(t, "unmapped") for t in terms}
    return ";".join(sorted(categories))

# ============================================================
# PROCESS DOCUMENT
# ============================================================
def process_document(row, extractor, health_terms, adaptation_terms, health_authority_terms, idx, total):
    doc_id = row["Document ID"]
    print(f"[{idx+1}/{total}] Processing Doc ID: {doc_id}")

    country = row.get("Geographies", "")
    year = row.get("Year", "")
    response = row.get("Topic/Response", "")
    content_url = row.get("Document Content URL", "")
    fallback_url = row.get("Document URL", "")

    extracted_text = ""
    notes = ""

    # 1️⃣ Try content_url first
    if isinstance(content_url, str) and content_url.startswith("http"):
        try:
            result = extractor.extract(content_url)
            if isinstance(result, dict):
                extracted_text = result.get("text", "")
            elif isinstance(result, str):
                extracted_text = result
        except Exception as e:
            print(f"   ⚠ Error extracting content_url: {e}")
            notes = f"content_url error: {e}"

    # 2️⃣ If extraction failed → try fallback_url
    if not extracted_text and isinstance(fallback_url, str) and fallback_url.startswith("http"):
        try:
            print("   → Trying fallback Document URL")
            result = extractor.extract(fallback_url)
            if isinstance(result, dict):
                extracted_text = result.get("text", "")
            elif isinstance(result, str):
                extracted_text = result
        except Exception as e:
            print(f"   ⚠ Error extracting fallback_url: {e}")
            notes += f" | fallback_url error: {e}"

    # 3️⃣ Translate & normalize
    text = ""
    if extracted_text and extracted_text.strip():
        try:
            text = detect_and_translate(extracted_text)
        except Exception as e:
            print(f"   ⚠ Translation failed: {e}")
            text = extracted_text
    else:
        notes = "Extraction failed"

    # Initialize default values
    health_relevance = 0
    health_mandate = 0
    institutional_role = 0
    matched_terms = ""
    mapped_categories = ""

    if text:
        words = text.split()
        extracted_chunks = []

        for i in range(0, len(words), CHUNK_SIZE):
            chunk_text = " ".join(words[i:i+CHUNK_SIZE])
            doc = nlp(chunk_text)
            sentences = [s.text for s in doc.sents]

            # Extract windows with health terms
            chunk_extract = extract_relevant_windows(chunk_text, health_terms)
            if chunk_extract:
                extracted_chunks.append(chunk_extract)

            # Institutional health role
            if contains_any(chunk_text, health_authority_terms):
                institutional_role = 1

            # Health adaptation mandate
            for s in sentences:
                if contains_any(s, health_terms) and (contains_any(s, adaptation_terms) or has_obligation(s)):
                    health_mandate = 1
                    break

        if extracted_chunks:
            combined_text = " ".join(extracted_chunks)
            matched_terms = extract_health_keywords(combined_text, health_terms)
            mapped_categories = map_terms_to_categories(matched_terms, health_term_categories)
            if matched_terms:
                health_relevance = 1

        del extracted_chunks
        gc.collect()

    return {
        "Doc ID": doc_id,
        "Country": country,
        "Year": year,
        "Response": response,
        "Health relevance (1/0)": health_relevance,
        "Health adaptation mandate (1/0)": health_mandate,
        "Institutional health role (1/0)": institutional_role,
        "Matched health keywords": matched_terms,
        "Health keyword categories": mapped_categories,
        "Notes": notes
    }


# ============================================================
# MAIN
# ============================================================

def main():
    logging.info("PIPELINE STARTED")

    health_terms = load_keyword_set(HEALTH_TERMS_FILE)
    adaptation_terms = load_keyword_set(ADAPTATION_TERMS_FILE)
    health_authority_terms = load_keyword_set(HEALTH_AUTHORITY_FILE)
    extractor = PDFExtractor()

    df = pd.read_csv(INPUT_DATA)
    df['Year'] = pd.to_datetime(df['First event in timeline'], errors='coerce').dt.year
    df = df[~df["Document Content URL"].isna()]

    total_docs = len(df)

    # Remove old output file if it exists
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    for idx, row in df.iterrows():

        try:
            row_result = process_document(
                row,
                extractor,
                health_terms,
                adaptation_terms,
                health_authority_terms,
                idx,
                total_docs
            )

        except Exception as e:
            logging.warning(f"Processing failed for index {idx}: {e}")

            # Even if it crashes, still save row with defaults
            row_result = {
                "Doc ID": row.get("Document ID", ""),
                "Country": row.get("Geographies", ""),
                "Year": row.get("Year", ""),
                "Response": row.get("Topic/Response", ""),
                "Health relevance (1/0)": 0,
                "Health adaptation mandate (1/0)": 0,
                "Institutional health role (1/0)": 0,
                "Matched health keywords": "",
                "Health keyword categories": "",
                "Notes": "Processing failed"
            }

        # ✅ SAVE AFTER EVERY DOCUMENT
        pd.DataFrame([row_result]).to_csv(
            OUTPUT_FILE,
            mode='a',
            index=False,
            header=not os.path.exists(OUTPUT_FILE)
        )

        print(f"[{idx+1}/{total_docs}] Saved Doc ID {row_result.get('Doc ID')}")

        # ✅ Free memory immediately
        del row_result
        gc.collect()

    logging.info("PIPELINE FINISHED")
    print("✔ Processing complete")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Log: {LOG_FILE}")


if __name__ == "__main__":
    main()

