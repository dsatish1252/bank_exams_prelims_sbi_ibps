import time
import html
import streamlit as st
import pandas as pd


# ============================================================
# CONFIG
# ============================================================

SECTION_ORDER = ["English Language", "Reasoning Ability", "Numerical Ability"]
SECTION_SECONDS = 20 * 60          # 20 minutes per section
POSITIVE_MARK = 1
NEGATIVE_MARK = 0.25               # set 0 for no negative marking
OPTION_COLS = [f"option {i}" for i in range(1, 6)]

# palette status -> (background, text colour, border, border-radius)
PAL_STYLE = {
    "answered":        ("#34b556", "#ffffff", "#34b556", "10px"),
    "not_answered":    ("#c62828", "#ffffff", "#c62828", "10px"),
    "marked":          ("#7e3f98", "#ffffff", "#7e3f98", "10px"),
    "marked_answered": ("#7e3f98", "#ffffff", "#7e3f98", "10px"),
    "not_visited":     ("#ffffff", "#202124", "#333333", "10px"),
}

st.set_page_config(
    page_title="Online Examination",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# HELPERS
# ============================================================

def render_html(markup: str):
    """Strip indentation/blank lines so Markdown never turns HTML into code."""
    cleaned = "\n".join(l.strip() for l in markup.splitlines() if l.strip())
    st.markdown(cleaned, unsafe_allow_html=True)


def clean(v):
    return "" if pd.isna(v) else str(v).strip()


def esc(text):
    return html.escape(text).replace("\n", "<br>")


def md_safe(text):
    return text.replace("$", "\\$")


def parse_correct(raw, options):
    """Correct option number (1-5) from 1 / '1' / 'A' / 'Option 1' / option text."""
    s = clean(raw).lower()
    if not s:
        return None
    try:
        n = int(float(s))
        return n if 1 <= n <= 5 else None
    except ValueError:
        pass
    s2 = s.replace("option", "").strip().strip("().:")
    if s2.isdigit() and 1 <= int(s2) <= 5:
        return int(s2)
    if len(s2) == 1 and s2 in "abcde":
        return "abcde".index(s2) + 1
    for n, text in options:
        if text.lower() == s:
            return n
    return None


def build_sections(df):
    sections = []
    for name in SECTION_ORDER:
        rows = df[df["section"] == name]
        questions = []
        for _, r in rows.iterrows():
            options = [(i + 1, clean(r[c])) for i, c in enumerate(OPTION_COLS) if clean(r[c])]
            questions.append({
                "question": clean(r["question"]),
                "options": options,
                "correct": parse_correct(r["correct option"], options),
            })
        sections.append({"name": name, "questions": questions})
    return sections


# ============================================================
# CSS (common)
# ============================================================

render_html("""
<style>
html, body, [data-testid="stAppViewContainer"] { margin: 0; padding: 0; }
[data-testid="stAppViewContainer"] { background: #ffffff; }
[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 100% !important; padding: 20px 32px 16px 32px !important; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stAlert"] { border-radius: 6px !important; }

/* Keep text readable on the white page even when Streamlit uses a dark theme */
[data-testid="stMetric"] * { color: #202124 !important; }
[data-testid="stTextInput"] label p { color: #202124 !important; }

/* ---------- Upload page ---------- */
.exam-header { display: flex; align-items: center; gap: 14px; margin-bottom: 4px; }
.exam-icon { font-size: 42px; line-height: 1; }
.exam-title { font-size: 32px; font-weight: 700; color: #202124; margin: 0; }
.exam-subtitle { margin: 5px 0 0 56px; font-size: 15px; color: #687385; }
.upload-title { font-size: 18px; font-weight: 600; color: #202124; margin-bottom: 5px; }
.upload-description { font-size: 14px; color: #687385; margin-bottom: 10px; }

[data-testid="stFileUploader"] { margin: 0 !important; padding: 0 !important; }
[data-testid="stFileUploader"] section {
    border: 1px solid #d8dde5 !important; border-radius: 7px !important;
    background: #fafbfc !important; padding: 7px 12px !important; min-height: 52px !important;
}
[data-testid="stFileUploader"] small { display: none !important; }
[data-testid="stFileUploader"] button {
    min-height: 32px !important; padding: 3px 16px !important;
    border-radius: 5px !important; font-size: 13px !important; font-weight: 600 !important;
}
[data-testid="stFileUploaderFile"] {
    margin-top: 5px !important; padding: 7px 10px !important; border-radius: 6px !important;
    border: 1px solid #d8dde5 !important; background: #f7f9fc !important;
}
.section-heading { margin-top: 18px; margin-bottom: 8px; font-size: 17px; font-weight: 700; color: #202124; }
.exam-info { margin-top: 18px; border: 1px solid #dfe3e8; border-radius: 8px; padding: 16px 20px; background: #ffffff; }
.exam-info-title { font-size: 17px; font-weight: 700; color: #202124; margin-bottom: 10px; }
.info-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.info-item { background: #f7f9fc; border: 1px solid #e2e6eb; border-radius: 6px; padding: 10px 12px; }
.info-label { font-size: 11px; color: #77808f; text-transform: uppercase; margin-bottom: 3px; }
.info-value { font-size: 15px; font-weight: 600; color: #202124; }
.file-note {
    margin-top: 10px; padding: 10px 14px; border: 1px solid #e1e5ea;
    border-radius: 6px; background: #fafbfc; color: #6b7280; font-size: 13px;
}

/* ---------- Generic buttons ---------- */
div.stButton > button {
    width: 100%; height: 40px; border-radius: 4px; border: none;
    background: #168aad; color: white; font-size: 15px; font-weight: 600;
}
div.stButton > button:hover { background: #117795; color: white; }
</style>
""")


# ============================================================
# CSS (exam page only: compact, fits the screen, only question box scrolls)
# ============================================================

EXAM_CSS = """
<style>
/* remove Streamlit's top header so nothing wastes vertical space */
[data-testid="stHeader"], [data-testid="stToolbar"] { display: none !important; }
.block-container { padding: 10px 28px 0 28px !important; }
[data-testid="stVerticalBlock"] { gap: 0.4rem !important; }

/* top bar */
.top-title { font-size: 17px; color: #202124; padding-top: 8px; }
.sec-time { text-align: right; font-size: 17px; font-weight: 700; color: #202124; }
.sec-time-label { margin-right: 10px; }
.tbox {
    display: inline-block; min-width: 28px; padding: 3px 5px; margin: 0 3px;
    background: #6b6b6b; color: #fff; border-radius: 3px; text-align: center; font-size: 16px;
}
.tbox.low { background: #c62828; }

/* tabs */
.tabs {
    display: flex; align-items: center; gap: 22px; padding: 6px 0 6px 4px;
    border-top: 1px solid #e3e6ea; border-bottom: 1px solid #e3e6ea; margin: 0;
}
.tabs-label { font-size: 13px; color: #444; padding-right: 18px; border-right: 1px solid #bbb; }
.tab { font-size: 15px; color: #333; padding: 6px 10px; border-radius: 3px; }
.tab.active { background: #17798a; color: #fff; }

/* question header */
.q-no { font-size: 16px; font-weight: 700; color: #202124; padding-top: 6px; }
.q-meta { text-align: right; font-size: 14px; color: #444; padding-top: 4px; }
.pill { display: inline-block; padding: 1px 12px; border-radius: 12px; color: #fff; font-size: 13px; font-weight: 700; margin-right: 6px; }
.pill.pos { background: #34b556; }
.pill.neg { background: #c62828; }
.q-time { margin-left: 14px; }
.q-time-label { color: #555; margin-right: 6px; }

/* QUESTION BOX: height follows the browser window, only this part scrolls */
.st-key-qbox {
    height: calc(100vh - 245px);
    min-height: 200px;
    overflow-y: auto;
    border: 1px solid #e3e6ea;
    border-radius: 6px;
    padding: 14px 18px;
    background: #ffffff;
}
.q-text { font-size: 17px; color: #202124; line-height: 1.6; margin-bottom: 12px; }

/* OPTIONS: force dark readable text + visible radio circles */
[data-testid="stRadio"] label { padding: 6px 0 !important; }
[data-testid="stRadio"] label *,
[data-testid="stRadio"] label p {
    color: #202124 !important;
    opacity: 1 !important;
    font-size: 16px !important;
}
[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child,
[data-testid="stRadio"] label[data-baseweb="radio"] > span:first-child {
    background-color: #ffffff !important;
    border: 2px solid #666666 !important;
}
[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child,
[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > span:first-child {
    background-color: #168aad !important;
    border-color: #168aad !important;
}

/* bottom action bar */
.st-key-btn_mark button, .st-key-btn_clear button {
    background: #b8d4ec !important; color: #202124 !important; border: 1px solid #9bbfdc !important; font-weight: 500 !important;
}
.st-key-btn_save button { background: #2cc3d4 !important; color: #fff !important; }
.st-key-btn_mark button:hover, .st-key-btn_clear button:hover { background: #a6c8e6 !important; }
.st-key-btn_save button:hover { background: #20a9b9 !important; }

/* right panel (scrolls only on very short windows) */
.st-key-sidepanel {
    background: #d3e9f1; padding: 10px 14px; border-radius: 4px;
    max-height: calc(100vh - 135px); overflow-y: auto;
}
.profile { display: flex; align-items: center; gap: 10px; font-size: 16px; color: #202124; }
.avatar { width: 36px; height: 36px; border-radius: 50%; background: #fff; display: flex; align-items: center; justify-content: center; font-size: 20px; }
.legend { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 4px; font-size: 12px; color: #202124; }
.lg-badge {
    display: inline-block; min-width: 24px; padding: 1px 5px; margin-right: 5px; text-align: center;
    color: #fff; font-weight: 700; font-size: 12px; border-radius: 6px;
}
.lg-badge.green { background: #34b556; }
.lg-badge.purple { background: #7e3f98; }
.lg-badge.red { background: #c62828; }
.lg-badge.white { background: #fff; color: #202124; border: 1px solid #333; }
.sec-strip { background: #b3d9e6; padding: 6px 10px; font-size: 14px; color: #202124; margin: 0 -14px; }

/* PALETTE: fixed rounded squares */
[class*="st-key-pal_"] [data-testid="stButton"],
[class*="st-key-pal_"] .stButton { display: flex; justify-content: center; }
[class*="st-key-pal_"] button {
    width: 40px !important; height: 40px !important; min-height: 40px !important;
    padding: 0 !important; border-radius: 10px !important;
    font-size: 14px !important; font-weight: 600 !important;
}

.st-key-btn_subsec button, .st-key-btn_subtest button { background: #2cc3d4 !important; color: #fff !important; height: 36px !important; }
.st-key-btn_subsec button:hover, .st-key-btn_subtest button:hover { background: #20a9b9 !important; }
[data-testid="stPopover"] button {
    width: 100%; height: 36px; background: #a9cde6 !important; color: #202124 !important;
    border: none !important; font-weight: 500 !important;
}
.confirm-box { background: #fff7e0; border: 1px solid #f0d58a; border-radius: 5px; padding: 8px 10px; font-size: 13px; color: #202124; }
</style>
"""


# ============================================================
# SESSION STATE
# ============================================================

DEFAULTS = {
    "exam_started": lambda: False,
    "finished": lambda: False,
    "sections": lambda: None,
    "section_idx": lambda: 0,
    "q_idx": lambda: 0,
    "answers": lambda: {},
    "marked": lambda: set(),
    "visited": lambda: set(),
    "section_start": lambda: None,
    "q_start": lambda: None,
    "confirm": lambda: None,
    "exam_title": lambda: "Online Examination",
    "candidate": lambda: "Candidate",
}


def init_state(force=False):
    for k, factory in DEFAULTS.items():
        if force or k not in st.session_state:
            st.session_state[k] = factory()


init_state()


# ---------- state actions (used as button callbacks) ----------

def start_exam(df, title, candidate):
    init_state(force=True)
    st.session_state.sections = build_sections(df)
    st.session_state.exam_title = title
    st.session_state.candidate = candidate or "Candidate"
    st.session_state.section_start = time.time()
    st.session_state.q_start = time.time()
    st.session_state.exam_started = True


def goto(i):
    st.session_state.q_idx = i
    st.session_state.q_start = time.time()


def go_next_section():
    st.session_state.confirm = None
    if st.session_state.section_idx < len(st.session_state.sections) - 1:
        st.session_state.section_idx += 1
        st.session_state.q_idx = 0
        st.session_state.section_start = time.time()
        st.session_state.q_start = time.time()
    else:
        st.session_state.finished = True


def save_next(si, qi, n):
    st.session_state.marked.discard((si, qi))
    if qi < n - 1:
        goto(qi + 1)


def mark_next(si, qi, n):
    st.session_state.marked.add((si, qi))
    if qi < n - 1:
        goto(qi + 1)


def clear_response(si, qi):
    st.session_state.answers.pop((si, qi), None)
    st.session_state.pop(f"radio_{si}_{qi}", None)


def ask_confirm(kind):
    st.session_state.confirm = kind


def cancel_confirm():
    st.session_state.confirm = None


def finish_test():
    st.session_state.confirm = None
    st.session_state.finished = True


def q_status(si, qi):
    a = (si, qi) in st.session_state.answers
    m = (si, qi) in st.session_state.marked
    v = (si, qi) in st.session_state.visited
    if m and a:
        return "marked_answered"
    if m:
        return "marked"
    if a:
        return "answered"
    if v:
        return "not_answered"
    return "not_visited"


# ============================================================
# PAGE 1: UPLOAD
# ============================================================

def show_upload_page():
    render_html("""
    <div class="exam-header">
        <div class="exam-icon">📝</div>
        <div class="exam-title">Online Examination</div>
    </div>
    <div class="exam-subtitle">Upload the MCQ question bank to start the examination.</div>
    """)
    st.write("")

    # Upload section takes only one quarter of the page width
    left, _ = st.columns([1, 3])
    with left:
        render_html("""
        <div class="upload-title">Upload MCQ Question Bank</div>
        <div class="upload-description">
            Select an Excel file containing the questions, options,
            correct answers and category.
        </div>
        """)
        uploaded_file = st.file_uploader(
            "Upload Excel", type=["xlsx", "xls"], label_visibility="collapsed"
        )
        candidate = st.text_input("Candidate name", value="Candidate")

    if uploaded_file is None:
        with left:
            render_html('<div class="file-note">Supported format: <b>.xlsx</b> or <b>.xls</b></div>')
        return

    try:
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.astype(str).str.strip().str.lower()

        required = ["question"] + OPTION_COLS + ["correct option", "category"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            st.error("The uploaded Excel file is missing these columns: " + ", ".join(missing))
            return

        df = df.dropna(subset=["question"]).reset_index(drop=True)
        df["category"] = df["category"].astype(str).str.strip().str.lower()

        category_mapping = {
            "english": "English Language",
            "english language": "English Language",
            "english_language": "English Language",
            "reasoning": "Reasoning Ability",
            "reasoning ability": "Reasoning Ability",
            "reasoning_ability": "Reasoning Ability",
            "numerical": "Numerical Ability",
            "numerical ability": "Numerical Ability",
            "numerical_ability": "Numerical Ability",
            "quantitative": "Numerical Ability",
            "quantitative aptitude": "Numerical Ability",
        }
        df["section"] = df["category"].map(category_mapping)

        invalid = df[df["section"].isna()]["category"].unique()
        if len(invalid) > 0:
            st.warning(
                "Some questions have categories that cannot be mapped to the "
                "three examination sections: " + ", ".join(map(str, invalid))
            )

        df = df[df["section"].notna()].reset_index(drop=True)
        if len(df) == 0:
            st.error("No valid questions were found in the uploaded file.")
            return

        eng = int((df["section"] == "English Language").sum())
        rea = int((df["section"] == "Reasoning Ability").sum())
        num = int((df["section"] == "Numerical Ability").sum())
        total = len(df)

        render_html('<div class="section-heading">Question Bank Loaded</div>')
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Questions", total)
        c2.metric("English Language", eng)
        c3.metric("Reasoning Ability", rea)
        c4.metric("Numerical Ability", num)

        render_html(f"""
        <div class="exam-info">
            <div class="exam-info-title">Examination Details</div>
            <div class="info-grid">
                <div class="info-item"><div class="info-label">Sections</div><div class="info-value">3</div></div>
                <div class="info-item"><div class="info-label">Section Time</div><div class="info-value">20 Minutes</div></div>
                <div class="info-item"><div class="info-label">Total Questions</div><div class="info-value">{total}</div></div>
                <div class="info-item"><div class="info-label">Total Duration</div><div class="info-value">60 Minutes</div></div>
            </div>
        </div>
        """)
        st.write("")

        if eng == 0 or rea == 0 or num == 0:
            st.error("The question bank must contain questions for all three sections.")
        else:
            if st.button("▶  START EXAMINATION", use_container_width=True):
                title = uploaded_file.name.rsplit(".", 1)[0] or "Online Examination"
                start_exam(df, title, candidate)
                st.rerun()

    except Exception as e:
        st.error(f"Unable to process the Excel file: {e}")


# ============================================================
# PAGE 2: EXAM
# ============================================================

@st.fragment(run_every=1)
def section_timer():
    remaining = SECTION_SECONDS - (time.time() - st.session_state.section_start)
    if remaining <= 0:
        go_next_section()
        st.rerun()
    h, rem = divmod(int(remaining), 3600)
    m, s = divmod(rem, 60)
    cls = "tbox low" if remaining < 60 else "tbox"
    render_html(
        f'<div class="sec-time"><span class="sec-time-label">Section Time</span>'
        f'<span class="{cls}">{h:02d}</span>:<span class="{cls}">{m:02d}</span>:'
        f'<span class="{cls}">{s:02d}</span></div>'
    )


@st.fragment(run_every=1)
def question_meta():
    el = int(time.time() - st.session_state.q_start)
    m, s = divmod(el, 60)
    render_html(
        f'<div class="q-meta"><span class="pill pos">+{POSITIVE_MARK:g}</span>'
        f'<span class="pill neg">-{NEGATIVE_MARK:g}</span>'
        f'<span class="q-time"><span class="q-time-label">Time</span>{m:02d}:{s:02d}</span></div>'
    )


def palette_css(si, n, qi):
    rules = []
    for i in range(n):
        bg, fg, bd, rad = PAL_STYLE[q_status(si, i)]
        k = f".st-key-pal_{si}_{i}"
        ring = "box-shadow:0 0 0 2px #168aad !important;" if i == qi else ""
        rules.append(
            f"{k} button{{background:{bg} !important;color:{fg} !important;"
            f"border:1px solid {bd} !important;border-radius:{rad} !important;{ring}}}"
        )
        rules.append(f"{k} button:hover{{background:{bg} !important;color:{fg} !important;}}")
        rules.append(f"{k} button p{{color:{fg} !important;}}")
    render_html("<style>" + "\n".join(rules) + "</style>")


def show_exam_page():
    ss = st.session_state
    si = ss.section_idx
    sections = ss.sections
    section = sections[si]
    questions = section["questions"]
    n = len(questions)
    qi = min(ss.q_idx, n - 1)
    q = questions[qi]
    answers = ss.answers

    # Section time already over while the page was idle
    if time.time() - ss.section_start >= SECTION_SECONDS:
        go_next_section()
        st.rerun()

    ss.visited.add((si, qi))
    render_html(EXAM_CSS)

    # ---------------- Top bar ----------------
    t1, t2 = st.columns([3, 2])
    with t1:
        render_html(f'<div class="top-title">{esc(ss.exam_title)}</div>')
    with t2:
        section_timer()

    # ---------------- Section tabs ----------------
    tabs = "".join(
        f'<span class="tab{" active" if i == si else ""}">{esc(s["name"])}</span>'
        for i, s in enumerate(sections)
    )
    render_html(f'<div class="tabs"><span class="tabs-label">SECTIONS</span>{tabs}</div>')

    main, side = st.columns([3.3, 1.1], gap="medium")

    # ---------------- Question area ----------------
    with main:
        h1, h2 = st.columns([1, 1])
        with h1:
            render_html(f'<div class="q-no">Question No. {qi + 1}</div>')
        with h2:
            question_meta()

        # Only this box scrolls (its height is set in EXAM_CSS)
        with st.container(key="qbox"):
            render_html(f'<div class="q-text">{esc(q["question"])}</div>')

            nums = [num for num, _ in q["options"]]
            texts = dict(q["options"])
            if nums:
                saved = answers.get((si, qi))
                idx = nums.index(saved) if saved in nums else None
                choice = st.radio(
                    "Select answer",
                    nums,
                    index=idx,
                    format_func=lambda x: texts[x],
                    key=f"radio_{si}_{qi}",
                    label_visibility="collapsed",
                )
                if choice is not None:
                    answers[(si, qi)] = choice
            else:
                st.info("No options available for this question.")

        # ---------- bottom action bar ----------
        b1, b2, b3, b4 = st.columns([1.5, 1.2, 2.6, 1.2])
        with b1:
            st.button("Mark for Review & Next", key="btn_mark",
                      on_click=mark_next, args=(si, qi, n), use_container_width=True)
        with b2:
            st.button("Clear Response", key="btn_clear",
                      on_click=clear_response, args=(si, qi), use_container_width=True)
        with b4:
            st.button("Save & Next", key="btn_save",
                      on_click=save_next, args=(si, qi, n), use_container_width=True)

    # ---------------- Right panel ----------------
    with side:
        with st.container(key="sidepanel"):
            counts = {k: 0 for k in PAL_STYLE}
            for i in range(n):
                counts[q_status(si, i)] += 1

            render_html(f"""
            <div class="profile"><div class="avatar">👤</div><div>{esc(ss.candidate)}</div></div>
            <div class="legend">
                <div><span class="lg-badge green">{counts['answered']}</span>Answered</div>
                <div><span class="lg-badge purple">{counts['marked']}</span>Marked</div>
                <div><span class="lg-badge white">{counts['not_visited']}</span>Not Visited</div>
                <div><span class="lg-badge purple">{counts['marked_answered']}</span>Marked and answered</div>
                <div><span class="lg-badge red">{counts['not_answered']}</span>Not Answered</div>
            </div>
            <div class="sec-strip"><b>SECTION :</b> {esc(section['name'])}</div>
            """)

            # Palette (rounded squares)
            palette_css(si, n, qi)
            for r in range(0, n, 5):
                cols = st.columns(5, gap="small")
                for j in range(5):
                    i = r + j
                    if i >= n:
                        break
                    label = f"{i + 1} ✓" if q_status(si, i) == "marked_answered" else str(i + 1)
                    cols[j].button(label, key=f"pal_{si}_{i}", on_click=goto, args=(i,))

            # Question Paper / Instructions
            p1, p2 = st.columns(2, gap="small")
            with p1:
                with st.popover("Question Paper", use_container_width=True):
                    with st.container(height=380):
                        for i, qq in enumerate(questions):
                            opts = "  \n".join(f"({num}) {md_safe(t)}" for num, t in qq["options"])
                            st.markdown(f"**Q{i + 1}.** {md_safe(qq['question'])}  \n{opts}")
                            st.divider()
            with p2:
                with st.popover("Instructions", use_container_width=True):
                    st.markdown(
                        f"- Each section is timed at **{SECTION_SECONDS // 60} minutes** and closes automatically.\n"
                        f"- Correct answer: **+{POSITIVE_MARK:g}**, wrong answer: **-{NEGATIVE_MARK:g}**.\n"
                        "- You cannot go back to a section after submitting it.\n"
                        "- **Mark for Review** flags a question; a marked question with an answer is still evaluated."
                    )

            # Submit Section / Submit Test
            s1, s2 = st.columns(2, gap="small")
            with s1:
                st.button("Submit Section", key="btn_subsec", on_click=ask_confirm, args=("section",))
            with s2:
                st.button("Submit Test", key="btn_subtest", on_click=ask_confirm, args=("test",))

            # Confirmation box
            if ss.confirm == "section":
                answered_here = sum(1 for i in range(n) if (si, i) in answers)
                render_html(
                    f'<div class="confirm-box">You have answered <b>{answered_here}</b> of <b>{n}</b> '
                    f'questions. Once submitted you cannot return to this section.</div>'
                )
                y, c = st.columns(2)
                y.button("Yes, submit", key="confirm_yes_sec", on_click=go_next_section)
                c.button("Cancel", key="confirm_no_sec", on_click=cancel_confirm)

            elif ss.confirm == "test":
                total_answered = len(answers)
                render_html(
                    f'<div class="confirm-box">Submit the whole test now? You have answered '
                    f'<b>{total_answered}</b> questions in total.</div>'
                )
                y, c = st.columns(2)
                y.button("Yes, submit", key="confirm_yes_test", on_click=finish_test)
                c.button("Cancel", key="confirm_no_test", on_click=cancel_confirm)


# ============================================================
# PAGE 3: RESULTS
# ============================================================

def show_results_page():
    render_html("""
    <div class="exam-header">
        <div class="exam-icon">🏁</div>
        <div class="exam-title">Examination Completed</div>
    </div>
    """)
    st.write("")

    answers = st.session_state.answers
    summary, review = [], []
    total_score = 0.0

    for si, sec in enumerate(st.session_state.sections):
        correct = wrong = 0
        for qi, q in enumerate(sec["questions"]):
            ans = answers.get((si, qi))
            status = "Not attempted"
            if ans is not None:
                if ans == q["correct"]:
                    correct += 1
                    status = "Correct"
                else:
                    wrong += 1
                    status = "Wrong"
            review.append({
                "Section": sec["name"],
                "Q No": qi + 1,
                "Question": q["question"],
                "Your Answer": ans if ans is not None else "-",
                "Correct Answer": q["correct"] if q["correct"] is not None else "-",
                "Result": status,
            })
        n = len(sec["questions"])
        score = correct * POSITIVE_MARK - wrong * NEGATIVE_MARK
        total_score += score
        summary.append({
            "Section": sec["name"],
            "Questions": n,
            "Attempted": correct + wrong,
            "Correct": correct,
            "Wrong": wrong,
            "Score": round(score, 2),
        })

    total_q = sum(s["Questions"] for s in summary)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Score", f"{total_score:.2f} / {total_q * POSITIVE_MARK:g}")
    c2.metric("Correct", sum(s["Correct"] for s in summary))
    c3.metric("Wrong", sum(s["Wrong"] for s in summary))

    render_html('<div class="section-heading">Section-wise Result</div>')
    st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)

    render_html('<div class="section-heading">Answer Review</div>')
    review_df = pd.DataFrame(review)
    st.dataframe(review_df, use_container_width=True, hide_index=True)

    st.download_button(
        "⬇ Download Review (CSV)",
        review_df.to_csv(index=False).encode("utf-8"),
        file_name="exam_review.csv",
        mime="text/csv",
    )

    st.write("")
    if st.button("🔄 Take Another Exam"):
        init_state(force=True)
        st.rerun()


# ============================================================
# ROUTER
# ============================================================

if st.session_state.finished:
    show_results_page()
elif st.session_state.exam_started:
    show_exam_page()
else:
    show_upload_page()