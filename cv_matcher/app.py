import os
import json
from google import genai
from google.genai.errors import APIError

MY_API_KEY = "AIzaSyArb4etGrvqpPQSBh32rlnjkDmZKOc8vzI"

if MY_API_KEY and MY_API_KEY != "AI_ATSLĒGA_ŠO_NEPIECIEŠAMS_AIZSTĀT":
    os.environ["GEMINI_API_KEY"] = MY_API_KEY
    print("API atslēga iestatīta, izmantojot os.environ.")
else:
    
    if not os.getenv("GEMINI_API_KEY"):
        print("KĻŪDA: Lūdzu, iestatiet mainīgo 'MY_API_KEY' koda iekšpusē vai vides mainīgo 'GEMINI_API_KEY'.")
        exit()

try:

    client = genai.Client()
except Exception as e:
    print(f"Kļūda, inicializējot Gemini klientu: {e}")
    exit()

schema = {
    "type": "object",
    "properties": {
        "match_score": {"type": "number", "description": "Atbilstības rādītājs no 0 līdz 100."},
        "summary": {"type": "string", "description": "Īss kopsavilkums par to, cik labi CV atbilst JD."},
        "strengths": {"type": "array", "items": {"type": "string"}, "description": "Galvenās prasmes/pieredze, kas atbilst JD."},
        "missing_requirements": {"type": "array", "items": {"type": "string"}, "description": "Svarīgas JD prasības, kas CV nav redzamas."},
        "verdict": {"type": "string", "description": "Galīgais ieteikums: 'strong match', 'possible match' vai 'not a match'."}
    },
    "required": ["match_score", "summary", "strengths", "missing_requirements", "verdict"]
}

def evaluate_cv(jd_path, cv_path, prompt_path, output_prefix):
    """Izsauc Gemini API, lai novērtētu CV atbilstību JD un ģenerētu pārskatus."""
    try:
        # 1. Nolasīt ievaddatus
        with open(jd_path, 'r', encoding='utf-8') as jd_file:
            jd_text = jd_file.read()
        with open(cv_path, 'r', encoding='utf-8') as cv_file:
            cv_text = cv_file.read()
        with open(prompt_path, 'r', encoding='utf-8') as prompt_file:
            prompt_template = prompt_file.read()

        final_prompt = prompt_template.format(jd_text=jd_text, cv_text=cv_text)

    except FileNotFoundError as e:
        print(f"Kļūda: Ievades fails nav atrasts. Pārliecinieties, vai ceļš '{e.filename}' ir pareizs.")
        return
    except Exception as e:
        print(f"Kļūda, lasot failus: {e}")
        return

    print(f"Novērtē CV: {output_prefix}...")

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=final_prompt,
            config={
                "temperature": 0.3,
                "response_mime_type": "application/json",
                "response_schema": schema
            }
        )
        

        if not response.text:
             print(f"Brīdinājums: Gemini atgrieza tukšu atbildi. {output_prefix} izlaišana.")
             return

    except APIError as e:

        if "API key not valid" in str(e):
             print("\nFATĀLA KĻŪDA: API atslēga NAV DERĪGA. Lūdzu, pārbaudiet vai ģenerējiet jaunu atslēgu.\n")
        print(f"Gemini API kļūda {output_prefix}: {e}")
        return
    except Exception as e:
        print(f"Neatpazīta kļūda, izsaucot Gemini: {e}")
        return


    try:
        result = json.loads(response.text)
    except json.JSONDecodeError:
        print(f"Kļūda: Gemini atgrieza nepareizu JSON formātu: \n{response.text}")
        return


    os.makedirs("outputs", exist_ok=True)


    json_path = f"outputs/{output_prefix}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        # Nodrošināt latviešu rakstzīmju pareizu attēlošanu
        json.dump(result, f, indent=2, ensure_ascii=False)
    

    report_md = f"""# {output_prefix.upper()} Atbilstības pārskats

## Kopsavilkums
- **Atbilstības līmenis (Match Score):** {result['match_score']}%
- **Ieteikums (Verdict):** `{result['verdict'].upper()}`

---

### Analīze
{result['summary']}

### Stiprās puses
Kandidāta galvenās prasmes un pieredze, kas atbilst darba aprakstam:
{' '.join(f"- {s}" for s in result['strengths'])}

### Trūkstošās prasības
Svarīgas JD prasības, kas CV nav redzamas:
{' '.join(f"- {m}" for m in result['missing_requirements'])}
"""

    report_path = f"outputs/{output_prefix}_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"Pabeigts: {output_prefix}. JSON saglabāts: {json_path}, Pārskats: {report_path}")

if __name__ == "__main__":
    JD_FILE = "sample_inputs/jd.txt"
    PROMPT_FILE = "prompt.md"

    if not os.path.exists(JD_FILE) or not os.path.exists(PROMPT_FILE):
        print("Lūdzu, pārliecinieties, ka 'sample_inputs/jd.txt' un 'prompt.md' ir izveidoti.")
    else:

        for i in range(1, 4):
            cv_file = f"sample_inputs/cv{i}.txt"
            if os.path.exists(cv_file):
                evaluate_cv(JD_FILE, cv_file, PROMPT_FILE, f"cv{i}")
            else:
                print(f"Brīdinājums: CV fails '{cv_file}' nav atrasts. Izlaiž.")
