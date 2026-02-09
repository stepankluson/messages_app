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
    # Hledá řádky typu: 20.1.2024 14:30 - Pepa: Ahoj
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
            # Pokud řádek nezačíná datem, je to pokračování minulé zprávy
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
                # 1. FACEBOOK (JSON)
                if file.name.endswith('.json'):
                    data = json.load(file)
                    if 'messages' in data:
                        for m in data['messages']:
                            m['source'] = 'facebook' # Označíme původ
                        all_messages.extend(data['messages'])
                
                # 2. WHATSAPP (TXT)
                elif file.name.endswith('.txt'):
                    # Přečteme textový soubor
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
            st.subheader("⏱️ Kdo z chatu odepisuje nejrychleji?")
            if 'date' in df.columns:
                df_speed = df.sort_values('date').copy()
                df_speed['prev_sender'] = df_speed['sender_name'].shift(1)
                df_speed['time_diff'] = df_speed['date'].diff()
                
                mask = (
                    (df_speed['sender_name'] != df_speed['prev_sender']) & 
                    (df_speed['time_diff'] > pd.Timedelta(seconds=5)) & 
                    (df_speed['time_diff'] < pd.Timedelta(hours=4))
                )
                
                valid_responses = df_speed[mask]
                speed_stats = valid_responses.groupby('sender_name')['time_diff'].median().dt.total_seconds().sort_values()
                st.bar_chart(speed_stats, color="#FFD700")
            else:
                st.warning("Missing time data.")

        with tab4:
            st.subheader("😊 vs 🤬 Index pozitivity")
            
            positive_words = ["jo", "jojo", "jj", "jasně", "jasne", "přesně", "presne", "určitě", "souhlas", "yep", "jop", "xd", "xdd", "xddd", "lol", "lmao", "rofl", "haha", "hahaha", "hehe", ":d", ":dd", "super", "skvěle", "skvele", "pecka", "bomba", "top", "topovka", "luxus", "nice", "najs", "cool", "fajn", "dobře", "dobre", "pohoda", "klídek", "chill", "cenim", "respekt", "frajer", "krása", "krasa", "god", "goat", "legenda", "díky", "diky", "děkuju", "miluju", "láska", "laska", "srdce", "štěstí", "radost", "gg", "wp", "ez", "win", "výhra", "vyhra"]
            negative_words = ["ne", "nn", "nene", "nikdy", "odmítám", "nesouhlasím", "kurva", "píča", "piča", "pica", "kokot", "debil", "idiot", "kretén", "kreten", "sračka", "sracka", "hovno", "prdel", "zmrd", "vyser", "nasrat", "fuck", "hnus", "odpad", "trash", "cringe", "bída", "bida", "fail", "chyba", "omg", "bruh", "smutek", "bolest", "au", "brečím", "škoda", "bohužel", "rip", "chcípám", "sere", "štve", "vadí", "nenávidím", "nesnáším", "otrava", "nuda", "noob", "bot", "report", "lagy", "prohra", "loss", "L"]
            
            def get_sentiment(text):
                text = str(text).lower()
                for char in [".", ",", "!", "?", "(", ")", '"']:
                    text = text.replace(char, "")
                words = text.split()
                score = 0
                for w in words:
                    if w in positive_words: score += 1
                    elif w in negative_words: score -= 1
                return score

            df_mood = df_text.copy()
            df_mood['sentiment_score'] = df_mood['content'].apply(get_sentiment)
            mood_ranking = df_mood.groupby('sender_name')['sentiment_score'].mean() * 100
            
            st.bar_chart(mood_ranking)
            st.info("💡 Kladná čísla = Pozitivní vibe. Záporná čísla = Negativní vibe.")

        with tab5:
            st.subheader("Prozkoumej výskyt určitého slova")
            
            search_term = st.text_input("Napiš slovo nebo frázi, kterou chceš najít (např. 'pivo', 'nevím', 'promiň'):")

            if search_term: 
                term = search_term.lower()
            
                mask = df['content'].astype(str).str.contains(term, case=False, regex=False)
                results = df[mask]
                
                if not results.empty:
                    st.success(f"Nalezeno **{len(results)}** zpráv obsahujících '{search_term}'!")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### 🏆 Kdo to píše nejčastěji?")
                        counts = results['sender_name'].value_counts()
                        st.bar_chart(counts)
                        
                    with col2:
                        st.markdown("### 📜 Poslední zmínky")
                        
                        ukazka = results[['date', 'sender_name', 'content']].sort_values('date', ascending=False).head(10)
                        st.dataframe(ukazka, use_container_width=True)
                        
                    st.markdown("### 📈 Trend slova v čase")
                    if 'date' in df.columns:
                        trend = results.set_index('date').resample('D').size()
                        
                        trend.name = "Počet výskytů"  
                        trend.index.name = "Datum"    
                        
                        st.bar_chart(trend) 
                        
                        st.caption("Graf ukazuje, kolikrát za měsíc padlo toto slovo.")
                else:
                    st.warning(f"Slovo '{search_term}' se v chatu nikde nevyskytuje. Jste slušní lidé! (Nebo to píšete jinak).")

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