import os
import requests
import pandas as pd
import streamlit as st

API = os.getenv("PODFLOW_API_URL", "http://127.0.0.1:8000").rstrip("/")
st.set_page_config(page_title="PODFlow AI", page_icon="🚚", layout="wide")
st.markdown("""
<style>
.stApp{background:#f4f7fb;color:#14243b}
.block-container{max-width:1280px;padding-top:1.2rem;padding-bottom:2rem}
.hero{background:#10233f;color:white;padding:24px 28px;border-radius:16px;margin-bottom:18px}
.hero h1{color:white;margin:0}.hero p{color:#d8e2ef;margin:7px 0 0}
div[data-testid="stMetric"]{background:white;border:1px solid #e5eaf1;padding:14px;border-radius:12px}
.stButton>button{border-radius:10px;min-height:42px}
</style>
""", unsafe_allow_html=True)

def headers():
    return {"Authorization": f"Bearer {st.session_state.get('token','')}"}

def api_get(path):
    r = requests.get(API + path, headers=headers(), timeout=15)
    r.raise_for_status()
    return r

def api_post(path, data=None, files=None):
    r = requests.post(API + path, data=data, files=files, headers=headers(), timeout=90)
    r.raise_for_status()
    return r

if "user" not in st.session_state:
    st.session_state.user = None
if not st.session_state.user:
    st.markdown('<div class="hero"><h1>🚚 PODFlow AI</h1><p>Proof of delivery, verified sooner.</p></div>', unsafe_allow_html=True)
    st.subheader("Sign in to your workspace")
    with st.form("login"):
        username = st.text_input("Username", placeholder="driver or billing")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Sign in", type="primary", use_container_width=True)
    if submit:
        try:
            r = requests.post(API + "/login", data={"username": username, "password": password}, timeout=15)
            r.raise_for_status()
            result = r.json()
            st.session_state.user = result
            st.session_state.token = result["access_token"]
            st.rerun()
        except Exception:
            st.error("Sign-in failed. Check your credentials and confirm that the API is running.")
    st.info("Demo accounts: driver / driver123 · billing / billing123")
    st.stop()

user = st.session_state.user
with st.sidebar:
    st.markdown("## 🚚 PODFlow AI")
    st.caption(f"{user['username']} · {user['role'].title()}")
    if st.button("Sign out", use_container_width=True):
        st.session_state.user = None
        st.session_state.token = ""
        st.rerun()
    pages = ["Capture POD", "My trips"] if user["role"] == "driver" else ["Overview", "Review queue", "Billing queue"]
    page = st.radio("Workspace", pages)

try:
    trips = api_get("/trips").json()
except Exception as exc:
    st.error("Backend unavailable. Start it with: uvicorn backend.main:app --reload")
    st.caption(str(exc))
    st.stop()

df = pd.DataFrame(trips)
st.markdown('<div class="hero"><h1>Proof of Delivery</h1><p>Capture the document. Resolve issues before billing.</p></div>', unsafe_allow_html=True)

if page == "Capture POD":
    st.subheader("📸 Delivery receipt capture")
    st.info("Driver: trip select karein, POD ki clear photo upload karein — stamp, signature aur LR number dikhna chahiye.")
    choices = {f"{t['trip_id']} · {t['destination']} · {t['client']}": t for t in trips}
    label = st.selectbox("Select your trip", list(choices))
    trip = choices[label]
    st.write(f"**Vehicle:** {trip['vehicle']}  ·  **LR:** {trip['lr']}  ·  **E-way bill:** {trip['eway']}")
    image = st.file_uploader("Take or choose POD photo", type=["jpg", "jpeg", "png", "webp"], help="On a phone, choose camera when prompted.")
    if image:
        st.image(image, caption="POD photo preview", width=360)
        if st.button("Upload and check POD", type="primary", use_container_width=True):
            try:
                response = api_post(f"/trips/{trip['trip_id']}/pod",
                    files={"file": (image.name, image.getvalue(), image.type or "image/jpeg")}).json()
                st.warning(response["message"])
                st.metric("Compressed image size", f"{response['size_bytes']:,} bytes")
                st.write(f"**OCR confidence:** {response['confidence']} · **LR match:** {response['lr_match']}")
                for flag in response["flags"]:
                    st.write("• " + flag)
                if response.get("extracted_text"):
                    with st.expander("OCR extracted text — verify manually"):
                        st.text(response["extracted_text"])
                st.success("Photo saved. Billing executive must review it before invoice.")
            except requests.HTTPError as exc:
                st.error(f"Upload failed: {exc.response.text}")
            except Exception as exc:
                st.error(f"Upload failed: {exc}")
    st.caption("Prototype limitation: this Streamlit web app needs a network connection to upload. It does not yet provide durable offline storage or automatic background sync.")

elif page == "My trips":
    st.subheader("My trip register")
    st.dataframe(df[["trip_id","destination","vehicle","lr","status","remarks"]], use_container_width=True, hide_index=True)
    st.caption("Status updates refresh when you reload the page.")

elif page == "Overview":
    st.subheader("Operations overview")
    a,b,c,d = st.columns(4)
    a.metric("Total trips", len(df))
    b.metric("Verified PODs", int((df.status == "Verified").sum()))
    c.metric("Missing PODs", int((df.status == "Missing POD").sum()))
    d.metric("Needs attention", int(df.status.isin(["Needs review","Retake requested"]).sum()))
    st.subheader("Trips by POD status")
    st.bar_chart(df.groupby("status").size())
    st.subheader("Missing PODs by branch")
    missing = df[df.status == "Missing POD"]
    if not missing.empty:
        st.bar_chart(missing.groupby("branch").size())
    else:
        st.success("No missing POD trips in current sample.")
    st.caption("POD-to-invoice cycle time is not calculated because the supplied sample has no reliable delivery and invoice timestamps.")

elif page == "Review queue":
    st.subheader("Billing executive · manual review")
    queue = [t for t in trips if t["status"] in ["Needs review","Retake requested"]]
    if not queue:
        st.success("Review queue clear.")
    for trip in queue:
        with st.expander(f"{trip['trip_id']} · {trip['client']} · {trip['status']}", expanded=True):
            st.write(f"Destination: {trip['destination']} · Freight: ₹{trip['freight']:,}")
            st.write(f"LR: {trip['lr']} · E-way bill: {trip['eway']}")
            st.write("Current notes:", trip["remarks"])
            if trip.get("pod_path"):
                try:
                    image_response = api_get(f"/trips/{trip['trip_id']}/pod-image")
                    st.image(image_response.content, caption="Original POD image — source of truth", width=420)
                except Exception:
                    st.warning("POD image is not available.")
            st.caption(f"Retake requests used: {trip.get('retake_count',0)} / 2")
            decision = st.selectbox("Review decision", ["Needs review","Verified","Retake requested"], key="decision_"+trip["trip_id"])
            notes = st.text_input("Reviewer notes", value=trip["remarks"], key="notes_"+trip["trip_id"])
            if st.button("Save review decision", key="save_"+trip["trip_id"]):
                try:
                    result = api_post(f"/trips/{trip['trip_id']}/review", data={"decision":decision,"remarks":notes}).json()
                    st.success(f"Saved: {result['status']}")
                    st.rerun()
                except requests.HTTPError as exc:
                    st.error(exc.response.text)
                except Exception as exc:
                    st.error(str(exc))

elif page == "Billing queue":
    st.subheader("Verified trips ready for billing")
    ready = [t for t in trips if t["status"] == "Verified" and t["invoice_status"] != "Exported"]
    if ready:
        billing = pd.DataFrame(ready)[["trip_id","client","lr","eway","vehicle","destination","freight","pod_path"]]
        st.dataframe(billing, use_container_width=True, hide_index=True)
        try:
            export_response = api_get("/billing/export.csv")
            st.download_button("Download Tally-ready CSV", export_response.content,
                file_name="podflow_tally_ready.csv", mime="text/csv", type="primary")
        except requests.HTTPError:
            st.warning("Export is not available.")
        st.caption("CSV is a Tally handoff template, not a direct Tally integration. POD image filenames are included for attachment matching.")
        for trip in ready:
            if st.button(f"Mark {trip['trip_id']} as exported", key="export_"+trip["trip_id"]):
                try:
                    api_post(f"/trips/{trip['trip_id']}/export")
                    st.success("Marked as exported.")
                    st.rerun()
                except requests.HTTPError as exc:
                    st.error(exc.response.text)
    else:
        st.info("No verified trips awaiting export.")
