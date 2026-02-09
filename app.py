import streamlit as st
import pandas as pd
import json
import networkx as nx
import matplotlib.pyplot as plt
import seaborn as sns
import re

st.set_page_config(page_title="Chat Analyzer Pro", layout="wide")

def fix_encoding(text):
    """Fixes Mojibake encoding (Latin-1 to UTF-8 conversion) for Facebook exports."""
    if isinstance(text, str):
        try:
            return text.encode('latin1').decode('utf-8')
        except:
            return text
    return text

def parse_whatsapp(text_content):
    """Převede WhatsApp TXT na seznam zpráv."""
    pattern = r'^(\d{1,2}\.\d{1,2}\.\d{2,4},? \s?\d{1,2}:\d{2}:?\d{0,2}) - (.*?): (.*)$'
    messages = []
    
    for line in text_content.split('\n'):
        match = re.match(pattern, line)
        if match:
            date_str, sender, content = match.groups()
            messages.append({
                'date_str': date_str, 
                'sender_name': sender.strip(),
                'content': content.strip(),
                'source': 'whatsapp'
            })
        elif messages: 
            messages[-1]['content'] += " " + line.strip()
            
    return messages

st.title("🚀 Ultimate WhatsApp/Messenger Analyzer")
st.markdown("Nahraj **jeden nebo více** JSON a TXT souborů (např. message_1.json, message_2.txt).")

with st.sidebar:
    st.header("📂 Nahrát data")
    st.markdown("Zde nahraj své soubory.")
    
    uploaded_files = st.file_uploader(
        "Vyber JSON/TXT soubory", 
        type=["json","txt"],
        accept_multiple_files=True
    )
    
    st.divider()
    st.info("Tip: Můžeš označit více souborů naráz.")

if uploaded_files:
    all_messages = []
    
    with st.spinner('Slepuji soubory a chroupu data... 🍪'):
        for file in uploaded_files:
            try:
                if file.name.endswith('.json'):
                    data = json.load(file)
                    if 'messages' in data:
                        for m in data['messages']:
                            m['source'] = 'facebook' 
                        all_messages.extend(data['messages'])
                
                elif file.name.endswith('.txt'):
                    string_data = file.read().decode("utf-8")
                    wa_msgs = parse_whatsapp(string_data)
                    all_messages.extend(wa_msgs)
                    
            except Exception as e:
                st.error(f"Chyba při načítání souboru {file.name}: {e}")

    if len(all_messages) > 0:
        df = pd.DataFrame(all_messages)
        
        df['date'] = pd.NaT 
        
        if 'timestamp_ms' in df.columns:
            df.loc[df['source']=='facebook', 'date'] = pd.to_datetime(df.loc[df['source']=='facebook', 'timestamp_ms'], unit='ms')
            
        if 'date_str' in df.columns:
            df.loc[df['source']=='whatsapp', 'date'] = pd.to_datetime(df.loc[df['source']=='whatsapp', 'date_str'], dayfirst=True, errors='coerce')
        
        df = df.dropna(subset=['date']).sort_values('date')
        
        df['sender_name'] = df['sender_name'].astype(str).apply(fix_encoding)
        df['content'] = df['content'].fillna('').astype(str).apply(fix_encoding)
        df_text = df[df['content'] != '']
        

        st.success(f"Úspěšně načteno {len(df)} zpráv z {len(uploaded_files)} souborů!")

        st.markdown("---")
        st.header("🏆 Síň slávy")
       
        top_sender = df['sender_name'].value_counts().idxmax()
        top_msg_count = df['sender_name'].value_counts().max()
        
        df['msg_length'] = df['content'].str.len()
        avg_lengths = df.groupby('sender_name')['msg_length'].mean()
        top_writer = avg_lengths.idxmax()
        top_writer_avg = int(avg_lengths.max())
        
        df['hour'] = df['date'].dt.hour
        night_msgs = df[(df['hour'] >= 0) & (df['hour'] < 5)]
        if not night_msgs.empty:
            top_owl = night_msgs['sender_name'].value_counts().idxmax()
            top_owl_count = night_msgs['sender_name'].value_counts().max()
        else:
            top_owl = "Nikdo (spíte?)"
            top_owl_count = 0

        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(label="👑 Největší Kecal", value=top_sender)
            # st.markdown vypíše normální text. Hvězdičky dělají tučné písmo.
            st.markdown(f"📝 **{top_msg_count}** zpráv") 
            
        with col2:
            st.metric(label="📖 Spisovatel", value=top_writer)
            st.markdown(f"📏 průměr **{top_writer_avg}** znaků")
            
        with col3:
            st.metric(label="🦉 Noční sova", value=top_owl)
            st.markdown(f"🌙 **{top_owl_count}** nočních zpráv")
            
        st.markdown("---")

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Přehled & Aktivita", 
            "🕸️ Sociomapa (Vztahy)", 
            "⚡ Rychlost odpovědí", 
            "🤬 Vibe Check",
            "🔍 Hledání slov",
            "🔥 Kdy to žije?"
        ])

        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🏆 Žebříček ukecanosti")
                # Tady můžeš taky zkusit změnit barvu, třeba na oranžovou
                st.bar_chart(df['sender_name'].value_counts(), color="#FF8C00") 

            with col2:
                st.subheader("📅 Aktivita v čase")
                if 'date' in df.columns:
                    timeline = df.set_index('date').resample('W').size()
                    
                    timeline.name = "Počet zpráv"
                    timeline.index.name = "Datum"
                    
                    st.line_chart(timeline, color=["#00CC96"]) 
                else:
                    st.warning("Chybí časová data.")

        with tab2:
            st.subheader("Kdo komu odpovídá?")
            st.write("Šipka ukazuje: 'Tenhle člověk reagoval na toho druhého'. (Funkce je vhodná hlavně pro skupinové chaty.)")
            
            df_net = df.sort_values('date').copy()
            df_net['target'] = df_net['sender_name'].shift(1)
            df_net = df_net.dropna(subset=['target'])
            df_net = df_net[df_net['sender_name'] != df_net['target']]
            
            relationships = df_net.groupby(['sender_name', 'target']).size().reset_index(name='weight')
            
            if not relationships.empty:
                G = nx.DiGraph()
                for _, row in relationships.iterrows():
                    if row['weight'] > 5:
                        G.add_edge(row['sender_name'], row['target'], weight=row['weight'])
                
                if len(G.nodes) > 0:
                    fig, ax = plt.subplots(figsize=(10, 8))
                    pos = nx.circular_layout(G)
                    nx.draw_networkx_nodes(G, pos, node_size=2500, node_color='skyblue', edgecolors='black', ax=ax)
                    max_weight = relationships['weight'].max()
                    edge_widths = [G[u][v]['weight'] / max_weight * 5 for u, v in G.edges()]
                    nx.draw_networkx_edges(G, pos, width=edge_widths, arrowstyle='-|>', arrowsize=20, edge_color='gray', alpha=0.7, ax=ax, connectionstyle="arc3,rad=0.1")
                    nx.draw_networkx_labels(G, pos, font_size=9, font_weight='bold', ax=ax)
                    ax.axis('off')
                    st.pyplot(fig)
                else:
                    st.warning("Po vyfiltrování slabých vazeb nezbylo nic k zobrazení.")
            else:
                st.error("Not enough interaction data.")

        with tab3: 
            st.subheader("⚡ Kdo je nejrychlejší v odepisování?")
            
            st.markdown("Graf ukazuje **medián** doby odezvy (běžná rychlost).")
            st.caption("⏱️ Údaje jsou v **sekundách**. (Ignorujeme pauzy delší než 4 hodiny, např. spánek).")

            df_s = df.sort_values('date').copy()
            df_s['diff'] = df_s['date'].diff()
            
            mask = (df_s['sender_name'] != df_s['sender_name'].shift(1)) & (df_s['diff'] < pd.Timedelta(hours=4))
            
            speed_data = df_s[mask].groupby('sender_name')['diff'].median().dt.total_seconds()
            
            speed_data = speed_data.sort_values(ascending=True)

            st.bar_chart(speed_data, color="#FF4B4B")

        with tab4: 
            st.subheader("😊 Kdo je největší pohodář a kdo pořád nadává?")
            
            st.markdown("Graf ukazuje průměrné **skóre nálady**.")
            st.caption("🔍 Uvedená stupnice je zjištěná na základě výskytů pozitivních a negativních slov ve zprávách.")

            pos_words = ["jo", "jj", "xd", "lol", "super", "diky", "top", "ok", "miluju", "haha"]
            neg_words = ["ne", "nn", "nuda", "bolest", "sere", "kurva", "nasrat", "trapny"]
            
            def get_mood(t):
                s = 0
                for w in str(t).lower().split():
                    if w in pos_words: s+=1
                    elif w in neg_words: s-=1
                return s
            
            if 'df_text' in locals():
                df_work = df_text.copy()
            else:
                df_work = df[df['content'] != ''].copy()

            df_work['mood'] = df_work['content'].apply(get_mood)
            
            mood_score = df_work.groupby('sender_name')['mood'].mean() * 100
            
            mood_score = mood_score.sort_values(ascending=False)

            st.bar_chart(mood_score, color="#FFD700")

        with tab5: # Hledání
            st.subheader("🔍 Napiš slovo u kterého tě zajímá četnost v chatu")
            
            # 1. Vylepšené vyhledávací pole
            col_search, col_limit = st.columns([3, 1])
            with col_search:
                term = st.text_input("Zadej slovo nebo frázi:", placeholder="např. pivo, miluju, nestíhám...")
            with col_limit:
                limit = st.number_input("Max zpráv", min_value=5, value=5, step=5)

            if term:
                # Filtrace (case=False znamená, že je jedno jestli napíšeš Pivo nebo pivo)
                mask = df['content'].str.contains(term, case=False, na=False)
                results = df[mask].sort_values('date', ascending=False) # Od nejnovějších
                
                if not results.empty:
                    st.success(f"Nalezeno **{len(results)}** zpráv.")
                    
                    # --- A) STATISTIKA KDO TO ŘÍKÁ ---
                    st.markdown("### 📊 Kdo to slovo používá nejčastěji?")
                    counts = results['sender_name'].value_counts().head(5)
                    st.bar_chart(counts, color="#0083B8") # Modrá barva
                    
                    st.divider()

                    # --- B) VÝPIS ZPRÁV JAKO CHAT ---
                    st.markdown("### 💬 Poslední zmínky v chatu")
                    
                    # Funkce pro zvýraznění slova (Highlighter)
                    def highlight_text(text, word):
                        # Použijeme Regular Expression pro náhradu bez ohledu na velikost písmen
                        pattern = re.compile(re.escape(word), re.IGNORECASE)
                        # Nahradíme nalezené slovo tím samým slovem, ale tučným a červeným
                        return pattern.sub(lambda m: f"**:red[{m.group(0)}]**", text)

                    # Smyčka přes nalezené zprávy (limitujeme počet, ať se to nezaseká)
                    for i, row in results.head(limit).iterrows():
                        sender = row['sender_name']
                        msg_text = row['content']
                        msg_date = row['date'].strftime("%d.%m.%Y %H:%M")
                        
                        # Zvýrazníme hledané slovo
                        highlighted_msg = highlight_text(msg_text, term)
                        
                        # Vykreslení bubliny (st.chat_message)
                        with st.chat_message(sender):
                            st.write(f"**{sender}** ({msg_date})")
                            st.markdown(highlighted_msg)
                            
                    if len(results) > limit:
                        st.info(f"... a dalších {len(results) - limit} zpráv (zvyš limit nahoře pro zobrazení).")
                        
                else:
                    st.warning(f"Slovo '{term}' nikdo nikdy nenapsal. 🤷‍♂️")
            else:
                st.info("👆 Napiš něco do vyhledávání.")

        with tab6:
            st.subheader("🔥 Kdy to v chatu nejvíc žije?")
            st.markdown("Tmavší barva = více zpráv. Kdy jste nejaktivnější?")

            if 'date' in df.columns:
                df_heat = df.copy()
                df_heat['hour'] = df_heat['date'].dt.hour
                df_heat['day_name'] = df_heat['date'].dt.day_name()
                
                days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                days_cz = ['Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek', 'Sobota', 'Neděle']
                
                heatmap_data = df_heat.groupby(['day_name', 'hour']).size().unstack(fill_value=0)
                
                heatmap_data = heatmap_data.reindex(days_order)
                
                fig, ax = plt.subplots(figsize=(12, 6))
                
                sns.heatmap(heatmap_data, cmap="YlOrRd", linewidths=.5, ax=ax, cbar_kws={'label': 'Počet zpráv'})
                
                ax.set_yticklabels(days_cz, rotation=0)
                ax.set_xlabel("Hodina (0 - 23)")
                ax.set_ylabel("Den v týdnu")
                ax.set_title("Intenzita konverzace podle času")
                
                st.pyplot(fig)
            else:
                st.warning("Chybí časová data pro heatmapu.")

    else:
        st.error("Uploaded files contain no valid messages.")