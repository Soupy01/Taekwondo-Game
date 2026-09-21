import json, random, sqlite3, uuid
from progress import ProgressStore
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="TKD Terminology Quest", page_icon="🥋", layout="centered")

DATA=json.loads((Path(__file__).parent/"questions.json").read_text(encoding="utf-8"))
GRADE_RANK={"10th":10,"9th":9,"8th":8,"7th":7,"6th":6,"5th":5,"4th":4,"3rd":3,"2nd":2,"1st":1}
DOBOKS=[
 ("Classic White",0,"🥋"),("Ocean Blue",60,"🥋"),("Forest Green",90,"🥋"),
 ("Purple Dragon",130,"🥋"),("Golden Champion",180,"🥋"),("Red Lightning",240,"🥋")
]
DOBOK_STYLE={
 "Classic White":("#f7f7f7","#111111","#e5e5e5"),
 "Ocean Blue":("#dceeff","#1666a8","#a8d5ff"),
 "Forest Green":("#e3f2e5","#24713b","#a9d7af"),
 "Purple Dragon":("#efe1ff","#6f35a5","#d0a7f4"),
 "Golden Champion":("#fff0ad","#b47b00","#ffd34e"),
 "Red Lightning":("#ffe0e0","#b51f2e","#ff8c8c"),
}
def dobok_card(name):
    base,trim,accent=DOBOK_STYLE.get(name,DOBOK_STYLE["Classic White"])
    svg=f"""<svg viewBox="0 0 220 230" width="145" height="150" xmlns="http://www.w3.org/2000/svg">
    <rect x="2" y="2" width="216" height="226" rx="22" fill="{base}" stroke="{trim}" stroke-width="3"/>
    <path d="M72 45L42 68L58 115L77 101L77 191L143 191L143 101L162 115L178 68L148 45L132 36L88 36Z"
    fill="white" stroke="{trim}" stroke-width="5" stroke-linejoin="round"/>
    <path d="M88 38L110 75L132 38M110 75L91 105M110 75L129 105" fill="none" stroke="{trim}" stroke-width="6"/>
    <rect x="77" y="121" width="66" height="11" rx="3" fill="{trim}"/>
    <path d="M61 76L48 106M159 76L172 106" stroke="{accent}" stroke-width="7" stroke-linecap="round"/>
    <circle cx="110" cy="157" r="12" fill="{accent}"/>
    <text x="110" y="216" text-anchor="middle" font-family="sans-serif" font-size="14" font-weight="bold" fill="{trim}">{name}</text>
    </svg>"""
    st.markdown(svg,unsafe_allow_html=True)

for k,v in {"coins":0,"owned":["Classic White"],"dobok":"Classic White","game":None,
            "index":0,"correct":0,"answered":False,"finished":False,
            "last_choice":None,"marked":False}.items():
    if k not in st.session_state: st.session_state[k]=v

st.title("🥋 TKD Terminology Quest")
st.caption("Questions are taken only from the Theory worksheet.")

def apply_profile(profile):
    st.session_state.player_id=profile["id"]
    st.session_state.player_name=profile["name"]
    for key in ("coins", "owned", "dobok"):
        st.session_state[key]=profile[key]


def sign_out():
    for key in list(st.session_state):
        del st.session_state[key]


try:
    store=ProgressStore()
except (sqlite3.Error, OSError):
    st.error("Cannot open saved player progress. Check that the game's data folder is writable, then reload.")
    st.stop()

if not st.session_state.get("player_id"):
    st.subheader("Your player profile")
    st.write("Sign in to restore your coins and doboks, or create a player to start saving progress.")
    account_action=st.radio("Player profile", ["Sign in", "Create player"], horizontal=True)
    with st.form("player_login", clear_on_submit=True):
        player_name=st.text_input("Player name", max_chars=40)
        password=st.text_input("Password", type="password", max_chars=128)
        if account_action=="Create player":
            confirm=st.text_input("Confirm password", type="password", max_chars=128)
            st.caption("Use at least 8 characters. Keep your name and password safe so you can return to your progress.")
        submitted=st.form_submit_button(account_action, type="primary")
    if submitted:
        try:
            if account_action=="Create player":
                if password!=confirm:
                    raise ValueError("The passwords do not match.")
                profile=store.create(player_name, password)
            else:
                profile=store.login(player_name, password)
            # Clear any previous unsaved round before loading this player's progress.
            sign_out()
            apply_profile(profile)
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except (sqlite3.Error, OSError):
            st.error("Could not open or save the player profile. Please try again.")
    st.stop()

try:
    apply_profile(store.load(st.session_state.player_id))
except (sqlite3.Error, OSError, ValueError):
    st.error("Could not load saved progress. Please reload and try again.")
    st.button("Sign out", on_click=sign_out)
    st.stop()


def award_coins(amount, event):
    try:
        apply_profile(store.reward(st.session_state.player_id, event, amount))
    except (sqlite3.Error, OSError, ValueError):
        st.error("Could not save your reward. Please try the action again.")
        st.stop()


def wear_dobok(name):
    try:
        apply_profile(store.equip(st.session_state.player_id, name,
                                 {name: price for name, price, _ in DOBOKS}))
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    except (sqlite3.Error, OSError):
        st.error("Could not save your dobok. Please try again.")
        st.stop()


with st.sidebar:
    st.header("Player")
    st.write(st.session_state.player_name)
    st.caption("Coins and doboks save automatically.")
    st.button("Sign out / switch player", on_click=sign_out)
    st.header("Choose your game")
    game_mode=st.radio("Game type",["Multiple Choice Game","Full Answer Theory Test","Dobok Shop"], key="game_selection")

    if game_mode!="Dobok Shop":
        st.header("Choose your challenge")
        grades=list(GRADE_RANK)
        g1=st.selectbox("From grade",grades,index=0)
        g2=st.selectbox("Through grade",grades,index=0)
        cats=["All"]+sorted({x["category"] for x in DATA if x.get("category")})
        category=st.selectbox("Category",cats)

        # Question Type is available in BOTH games.
        question_types=["All"]+sorted({
            str(x.get("type","")).strip() for x in DATA
            if str(x.get("type","")).strip()
        })
        question_type=st.selectbox("Question Type",question_types)

        # Question Source replaces the old Full / Partial classification and
        # is only shown for the Full Answer Theory Test.
        if game_mode=="Full Answer Theory Test":
            question_sources=["All"]+sorted({
                str(x.get("question_source","")).strip() for x in DATA
                if str(x.get("question_source","")).strip()
            })
            question_source=st.selectbox("Question Source",question_sources)
        else:
            question_source="All"

        count_choice=st.selectbox("Questions",[5,10,15,20,25,50,100,200,360,"All available"],index=1)
        count=999999 if count_choice=="All available" else int(count_choice)

    st.divider()
    st.metric("Coins",f"🪙 {st.session_state.coins}")
    st.write("Wearing:",st.session_state.dobok)

def filtered():
    lo=min(GRADE_RANK[g1],GRADE_RANK[g2]); hi=max(GRADE_RANK[g1],GRADE_RANK[g2])
    out=[]
    for q in DATA:
        rank=GRADE_RANK.get(q.get("grade"))
        if rank is None or not lo<=rank<=hi: continue
        if category!="All" and q.get("category")!=category: continue

        qtype=str(q.get("type","")).strip()
        if question_type!="All" and qtype!=question_type:
            continue

        if game_mode=="Full Answer Theory Test":
            qsource=str(q.get("question_source","")).strip()
            if question_source!="All" and qsource!=question_source:
                continue

        # Full Answer Test must use the Examiner Style Question column.
        if game_mode=="Full Answer Theory Test":
            examiner=str(q.get("examiner","")).strip()
            if not examiner or examiner.upper()=="N/A": continue

        if not str(q.get("answer","")).strip(): continue
        out.append(q)
    return out

def start():
    pool=filtered()
    minimum=4 if game_mode=="Multiple Choice Game" else 1
    if len(pool)<minimum:
        st.error("That selection does not contain enough suitable questions. Try a wider grade range, category, Question Type or Question Source selection.")
        return

    chosen=random.sample(pool,min(count,len(pool)))
    game=[]
    for q in chosen:
        if game_mode=="Full Answer Theory Test":
            prompt=q["examiner"]
        else:
            prompt=q["question"]

        item={"prompt":prompt,"correct":q["answer"],
              "meta":f'{q["grade"]} Kup • {q["type"]} • {q["category"]}'}

        if game_mode=="Multiple Choice Game":
            same=[x["answer"] for x in pool if x is not q and x["answer"]!=q["answer"]
                  and x.get("category")==q.get("category")]
            others=[x["answer"] for x in pool if x is not q and x["answer"]!=q["answer"]]
            distract=list(dict.fromkeys(same+others))
            random.shuffle(distract)
            opts=distract[:3]+[q["answer"]]
            random.shuffle(opts)
            item["options"]=opts
        game.append(item)

    for key in list(st.session_state):
        if key.startswith(("typed", "mc")):
            del st.session_state[key]
    st.session_state.round_id=uuid.uuid4().hex
    st.session_state.game=game
    st.session_state.game_mode_active=game_mode
    st.session_state.index=0
    st.session_state.correct=0
    st.session_state.answered=False
    st.session_state.finished=False
    st.session_state.last_choice=None
    st.session_state.marked=False

def advance_question():
    if st.session_state.finished:
        return
    if st.session_state.index+1>=len(st.session_state.game):
        if st.session_state.correct==len(st.session_state.game):
            award_coins(25, f"{st.session_state.round_id}:perfect")
        st.session_state.finished=True
    else:
        st.session_state.index+=1
        st.session_state.answered=False
        st.session_state.last_choice=None
        st.session_state.marked=False


def mark_and_advance(correct):
    if not st.session_state.answered or st.session_state.marked or st.session_state.finished:
        return
    if correct:
        award_coins(5, f"{st.session_state.round_id}:question:{st.session_state.index}")
        st.session_state.correct+=1
    st.session_state.marked=True
    advance_question()


if game_mode!="Dobok Shop":
    st.sidebar.button("Start new game",use_container_width=True,on_click=start)

if game_mode!="Dobok Shop":
    hero1,hero2=st.columns([1,2])
    with hero1:
        dobok_card(st.session_state.dobok)
    with hero2:
        st.markdown("### Your Dobok")
        st.write(f"**{st.session_state.dobok}**")
        st.write(f"🪙 **{st.session_state.coins} coins**")
    st.divider()
    game=st.session_state.game
    if not game:
        st.info("Choose a game and challenge in the sidebar, then press **Start new game**.")
    elif st.session_state.finished:
        total=len(game)
        st.success(f"Challenge complete — {st.session_state.correct}/{total} correct!")
        st.metric("Coin balance",f"🪙 {st.session_state.coins}")
        st.button("Play another round",on_click=start)
    else:
        i=st.session_state.index; q=game[i]
        mode=st.session_state.get("game_mode_active","Multiple Choice Game")
        st.progress(i/len(game),text=f"Question {i+1} of {len(game)}")
        st.caption(f"{mode} • {q['meta']}")
        st.subheader(q["prompt"])

        if mode=="Multiple Choice Game":
            choice=st.radio("Choose an answer",q["options"],index=None,key=f"mc{i}",
                            disabled=st.session_state.answered)
            if not st.session_state.answered:
                if st.button("Check answer",type="primary",disabled=choice is None):
                    if choice==q["correct"]:
                        award_coins(5, f"{st.session_state.round_id}:question:{i}")
                        st.session_state.correct+=1
                    st.session_state.last_choice=choice
                    st.session_state.answered=True
                    st.rerun()
            else:
                if st.session_state.last_choice==q["correct"]:
                    st.success("⭐ Correct! +5 coins")
                else:
                    st.error("Not this time.")
                    st.info(f"Correct answer: **{q['correct']}**")
        else:
            if not st.session_state.answered:
                with st.form(f"answer_form_{i}"):
                    typed=st.text_area("Type your full answer",key=f"typed{i}",height=120)
                    st.caption("Press Ctrl+Enter (Command+Enter on Mac) to check your answer.")
                    submitted=st.form_submit_button("Check answer",type="primary")
                if submitted:
                    if typed.strip():
                        st.session_state.last_choice=typed.strip()
                        st.session_state.answered=True
                        st.rerun()
                    else:
                        st.warning("Type an answer before checking it.")
            elif not st.session_state.marked:
                st.write("**Your answer:**"); st.write(st.session_state.last_choice)
                st.write("**Theory answer:**"); st.info(q["correct"])
                st.caption("Compare the answers, then mark yours to continue. Correct answers earn 5 coins.")
                action="finish" if i+1==len(game) else "next"
                c1,c2=st.columns(2)
                c1.button(f"Correct & {action}",use_container_width=True,
                          on_click=mark_and_advance,args=(True,),key=f"correct{i}")
                c2.button(f"Incorrect & {action}",use_container_width=True,
                          on_click=mark_and_advance,args=(False,),key=f"incorrect{i}")
            else:
                st.info(f"Theory answer: **{q['correct']}**")

        ready=st.session_state.answered and (mode=="Multiple Choice Game" or st.session_state.marked)
        if ready:
            st.write(f"Score: **{st.session_state.correct}/{i+1}** · Coins: **🪙 {st.session_state.coins}**")
            st.button("Next question",type="primary",key=f"next{i}",on_click=advance_question)

if game_mode=="Dobok Shop":
    st.header("Dobok Shop")
    st.caption("Earn 5 coins per correct answer and 25 bonus coins for a perfect round. Buying a dobok equips it straight away.")
    st.write(f"You have **🪙 {st.session_state.coins} coins**.")
    for name,price,icon in DOBOKS:
        owned=name in st.session_state.owned
        cols=st.columns([2,3,2])
        with cols[0]:
            dobok_card(name)
        cols[1].write(f"**{name}**")
        cols[1].caption("Owned" if owned else f"{price} coins")
        if name==st.session_state.dobok:
            cols[2].button("Equipped",key=f"eq-{name}",disabled=True,use_container_width=True)
        elif owned:
            if cols[2].button("Wear",key=f"wear-{name}",use_container_width=True):
                wear_dobok(name); st.rerun()
        else:
            if cols[2].button(f"Buy 🪙{price}",key=f"buy-{name}",use_container_width=True,
                              disabled=st.session_state.coins<price):
                wear_dobok(name)
                st.rerun()
        st.divider()

st.caption("Question Type can be filtered in both games. Full Answer Theory Test also uses Question Source and the Examiner Style Question field. Direction is fixed and hidden.")
