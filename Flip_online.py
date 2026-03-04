import streamlit as st  
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import numpy as np
from math import radians, cos, sin, asin, sqrt
import plotly.graph_objects as go
import base64
from gtts import gTTS
import io
import google.generativeai as genai  # <-- NEW: AI Engine

# 1. TACTICAL COMMAND UI
st.set_page_config(page_title="Flip Mining AI | Master Command", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0d11; color: #d1d1d1; font-family: 'Courier New', monospace; }
    .stMetric { background-color: #14171d; border: 1px solid #3d4450; padding: 15px; border-radius: 5px; }
    [data-testid="stMetricValue"] { color: #FFD700 !important; font-size: 28px !important; font-weight: bold; }
    [data-testid="stSidebar"] { background-color: #080a0d; border-right: 1px solid #3d4450; min-width: 380px !important; }
    .nav-btn {
        background-color: #FFD700; color: black !important; padding: 18px;
        text-align: center; border-radius: 12px; text-decoration: none;
        font-weight: bold; display: block; margin-bottom: 25px; border: 2px solid #b8860b;
    }
    .nav-btn:hover { background-color: #e6c200; transform: scale(1.02); transition: 0.2s; }
    </style>
    """, unsafe_allow_html=True)

# 2. ENGINES (Voice, GNSS, & AI)
def speak_command(text):
    """Triggers AI voice instructions for field operation."""
    try:
        tts = gTTS(text=text, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        b64 = base64.b64encode(fp.read()).decode()
        md = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
        st.markdown(md, unsafe_allow_html=True)
    except: pass

def calculate_m(lat1, lon1, lat2, lon2):
    """Precision distance between truck and mineral target."""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    c = 2 * asin(sqrt(sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2))
    return round(c * 6371 * 1000, 1)

# --- NEW: AI CONNECTION LOGIC ---
def get_ai_response(prompt, context_data):
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        full_query = f"Context: {context_data}. User Question: {prompt}"
        response = model.generate_content(full_query)
        return response.text
    except Exception as e:
        return f"AI Offline. Please check your API key in Secrets. Error: {e}"

# 3. SIDEBAR AUTH & MASTER DATA
st.sidebar.title("🔐 FIELD COMMAND")
admin_key = st.sidebar.text_input("Admin Access Key:", type="password")

if admin_key == "SouthSudan2026":
    st.sidebar.success("AUTH: OWNER VERIFIED")
    
    GOLD_PRICE_KG = 173200 

    @st.cache_data
    def load_data():
        # Simulation of millions of items logic
        file_path = 'discovery_log.csv'
        if not os.path.exists(file_path):
            data = []
            for i in range(1, 1001): 
                is_k = i > 500
                data.append({
                    'Flip_ID': f'FLIP-{i:06}', 'Mineral': 'Gold',
                    'Zone': 'Kapoeta Corridor' if is_k else 'Luri Watershed',
                    'Lat': round(np.random.uniform(4.7, 4.8) if is_k else np.random.uniform(4.8, 4.9), 6),
                    'Lon': round(np.random.uniform(33.5, 33.6) if is_k else np.random.uniform(31.1, 31.2), 6),
                    'Depth_M': round(np.random.uniform(2, 40), 1),
                    'Est_KG': round(np.random.uniform(2.0, 15.0), 2),
                    'Confidence': round(np.random.uniform(75.0, 98.8), 1)
                })
            df = pd.DataFrame(data)
            df.to_csv(file_path, index=False)
        else:
            df = pd.read_csv(file_path)
        return df

    df = load_data()
    
    # 4. NAVIGATION SEARCH
    search_q = st.sidebar.text_input("🔍 SEARCH MILLIONS OF SITES:", "").upper()
    filtered_list = df[df['Flip_ID'].str.contains(search_q)]['Flip_ID'].tolist() if search_q else df['Flip_ID'].tolist()
    
    target_id = st.sidebar.selectbox("🎯 SELECT TARGET SITE:", filtered_list)
    target = df[df['Flip_ID'] == target_id].iloc[0]

    st.sidebar.subheader("🚚 UNIT COORDINATION")
    u_lat = st.sidebar.number_input("Unit Lat:", value=float(target['Lat']) + 0.00004, format="%.6f")
    u_lon = st.sidebar.number_input("Unit Lon:", value=float(target['Lon']) + 0.00004, format="%.6f")
    dist_m = calculate_m(u_lat, u_lon, target['Lat'], target['Lon'])

    # 5. MAIN INTERFACE
    st.title(f"MISSION: {target_id} | {target['Zone']}")
    
    maps_url = f"https://www.google.com/maps/dir/?api=1&destination={target['Lat']},{target['Lon']}&travelmode=driving"
    st.markdown(f'<a href="{maps_url}" target="_blank" class="nav-btn">🧭 LAUNCH GOOGLE MAPS NAVIGATION</a>', unsafe_allow_html=True)

    c1, c2 = st.columns([2, 1])
    with c1:
        m = folium.Map(location=[target['Lat'], target['Lon']], zoom_start=19, 
                       tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google Satellite')
        folium.Marker([u_lat, u_lon], icon=folium.Icon(color='blue', icon='truck', prefix='fa')).add_to(m)
        folium.Marker([target['Lat'], target['Lon']], icon=folium.Icon(color='orange', icon='crosshairs', prefix='fa')).add_to(m)
        st_folium(m, width=900, height=450)

    with c2:
        st.subheader("🌋 Subsurface Profile")
        fig = go.Figure(data=[go.Scatter3d(
            x=[0, 0], y=[0, 0], z=[0, -target['Depth_M']],
            mode='lines+markers+text',
            line=dict(color='#FFD700', width=12),
            marker=dict(size=[0, 15], color=['#444', '#FFD700']),
            text=["Surface", f"TARGET @ {target['Depth_M']}M"],
            textposition="top center"
        )])
        fig.update_layout(scene=dict(xaxis_visible=False, yaxis_visible=False, bgcolor="black"),
                          margin=dict(l=0, r=0, b=0, t=0), height=450, paper_bgcolor="black")
        st.plotly_chart(fig, use_container_width=True)

    # 6. METRICS
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("DISTANCE", f"{dist_m} M")
    m2.metric("AI CONFIDENCE", f"{target.get('Confidence', 'N/A')}%")
    m3.metric("VALUE (USD)", f"${(target['Est_KG'] * GOLD_PRICE_KG):,.2f}")
    m4.metric("DIG DEPTH", f"{target['Depth_M']} M")

    # 7. --- NEW: TACTICAL AI CHAT BOX ---
    st.subheader("🤖 Tactical AI Assistant")
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Ask about this site geology..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        with st.chat_message("assistant"):
            context = f"Site {target_id} in {target['Zone']}. Depth: {target['Depth_M']}m. Gold: {target['Est_KG']}kg. Confidence: {target['Confidence']}%."
            response = get_ai_response(prompt, context)
            st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

    # 8. SEARCHABLE LEDGER
    st.subheader("📋 Operations Ledger")
    st.dataframe(df[df['Flip_ID'].str.contains(search_q)] if search_q else df.head(100), use_container_width=True, hide_index=True)

else:
    st.title("🛡️ Flip Mining AI: Secure Portal")
    st.warning("Enter Access Key to sync Satellite & GNSS data.")