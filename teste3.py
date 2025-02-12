import matplotlib.colors as mcolors
from matplotlib import cm
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import datetime
import streamlit as st
import numpy as np
import altair as alt
from streamlit_extras.let_it_rain import rain

# Configuração de layout (wide)
st.set_page_config(layout="wide")

# Carregar o arquivo CSV
file_path = "carnaval2025_updated.csv"
df = pd.read_csv(file_path)

st.dataframe(df)

# Converter colunas para formato datetime
df["inicio_data"] = pd.to_datetime(df["inicio_data"])
df["inicio_horario"] = pd.to_datetime(df["inicio_horario"], format="%H:%M:%S").dt.time
df["fim_data"] = pd.to_datetime(df["fim_data"])
df["fim_horario"] = pd.to_datetime(df["fim_horario"], format="%H:%M:%S").dt.time

# Criar colunas combinadas de data e hora
df["inicio_datetime"] = df.apply(lambda row: datetime.datetime.combine(row["inicio_data"], row["inicio_horario"]), axis=1)
df["fim_datetime"] = df.apply(lambda row: datetime.datetime.combine(row["fim_data"], row["fim_horario"]), axis=1)

# Expandir o intervalo de tempo de cada evento (hora a hora)
time_range = []
for _, row in df.iterrows():
    current_time = row["inicio_datetime"]
    while current_time <= row["fim_datetime"]:
        time_range.append({
            "data": row["inicio_data"],
            "hora": current_time.hour,
            "cpr": row["cpr"],
            "publico_previsto": row["publico_previsto"],
            "efetivo": row["efetivo"]
        })
        current_time += datetime.timedelta(hours=1)

df_expanded = pd.DataFrame(time_range)
st.dataframe(df_expanded)

st.title("Análise de Público no Carnaval 2025")
#rain(emoji="🎉", font_size=80, falling_speed=5, animation_length=1)

# Selecionar data e CPR
with st.container():
    # Converter a coluna "data" para o formato date
    df_expanded["data"] = pd.to_datetime(df_expanded["data"]).dt.date
    selected_data = st.selectbox("Selecione a Data", df_expanded["data"].unique())
    df_daily = df_expanded[df_expanded["data"] == selected_data]
    selected_cpr = st.selectbox("Selecione o CPR", df_daily["cpr"].unique())
    df_cpr = df_daily[df_daily["cpr"] == selected_cpr]

# ------------------------------
# Gráfico 1: Heatmap e Quantidade de Eventos por Hora
# ------------------------------

# Criar heatmap de público previsto (pivot table)
heatmap_data = df_cpr.pivot_table(
    index="hora", 
    columns="data", 
    values="publico_previsto", 
    aggfunc='sum', 
    fill_value=0
)
heatmap_data = heatmap_data.replace(0, np.nan)  # Evita muitos zeros

# Contagem de eventos por horário
eventos_por_horario = df_cpr.groupby("hora").size().reset_index(name="num_eventos")

# Mesclar os dados (opcional para a exibição)
df_juntos = pd.merge(df_cpr, eventos_por_horario, on="hora")

st.subheader("Público Previsto Acumulado por Hora")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7), dpi=600, gridspec_kw={'width_ratios': [3, 1]})

# Heatmap no ax1
sns.heatmap(
    heatmap_data, 
    cmap="coolwarm", 
    linewidths=0.5, 
    annot=True, 
    fmt="d", 
    xticklabels=False, 
    ax=ax1
)
ax1.set_xlabel("")
ax1.set_ylabel("Hora do Dia", fontsize=12)
ax1.set_title(f"Público Previsto Acumulado x Horário - {selected_data} - {selected_cpr}")
ax1.yaxis.set_tick_params(rotation=0)

# Mapear cores com base no número de eventos
norm = plt.Normalize(eventos_por_horario["num_eventos"].min(), eventos_por_horario["num_eventos"].max())
colors = cm.coolwarm(norm(eventos_por_horario["num_eventos"]))

# Filtrar horários com eventos e plotar gráfico de barras no ax2
eventos_por_horario_filtrado = eventos_por_horario[eventos_por_horario["num_eventos"] > 0]
ax2.barh(
    eventos_por_horario_filtrado["hora"], 
    eventos_por_horario_filtrado["num_eventos"], 
    color=colors, 
    alpha=0.7
)
ax2.set_yticks(eventos_por_horario_filtrado["hora"])
ax2.set_yticklabels(eventos_por_horario_filtrado["hora"])
ax2.set_ylabel("")
ax2.set_xlabel("Número de Eventos")
ax2.set_title("Quantidade de Eventos por Hora")
ax2.invert_yaxis()
ax2.grid(axis='x', linestyle='--', alpha=0.5)

plt.tight_layout(pad=2)
plt.savefig("heatmap.png", dpi=600, bbox_inches='tight', pad_inches=0.1)
st.pyplot(fig)

# ------------------------------
# Gráfico 2: Distribuição do Público Previsto e Efetivo (Layer Chart Altair)
# ------------------------------

# Agregar os valores por hora: somar público previsto e efetivo
df_agg = df_cpr.groupby("hora").agg({
    "publico_previsto": "sum",
    "efetivo": "sum"
}).reset_index()

# Calcular a quantidade de eventos por hora
eventos_por_horario_agg = df_cpr.groupby("hora").size().reset_index(name="Número de Eventos")

# Juntar as informações agregadas com a quantidade de eventos
df_agg = pd.merge(df_agg, eventos_por_horario_agg, on="hora")

# Mapear as cores com base na quantidade de eventos
norm = mcolors.Normalize(vmin=df_agg["Número de Eventos"].min(), vmax=df_agg["Número de Eventos"].max())
color_mapper = cm.ScalarMappable(norm=norm, cmap="coolwarm")
df_agg["color"] = df_agg["Número de Eventos"].apply(lambda x: mcolors.rgb2hex(color_mapper.to_rgba(x)))

# Exibir o dataframe agregado (opcional)
st.dataframe(df_agg)

st.subheader("Distribuição do Público Previsto e Efetivo por Hora e Quantidade de Eventos")

# Gráfico de barras para 'publico_previsto'
bar_chart = alt.Chart(df_agg).mark_bar().encode(
    x=alt.X("hora:O", title="Hora do Dia"),
    y=alt.Y("publico_previsto:Q", title="Público Previsto"),
    color=alt.Color("color:N", scale=None),
    tooltip=[
        alt.Tooltip("hora:O", title="Hora"),
        alt.Tooltip("publico_previsto:Q", title="Público Previsto"),
        alt.Tooltip("Número de Eventos:Q", title="Número de Eventos")
    ]
)

# Gráfico de linha (com pontos) para 'efetivo'
line_chart = alt.Chart(df_agg).mark_line(point=True, color="black", size=2).encode(
    x=alt.X("hora:O", title="Hora do Dia"),
    y=alt.Y("efetivo:Q", title="Público Efetivo"),
    tooltip=[
        alt.Tooltip("hora:O", title="Hora"),
        alt.Tooltip("efetivo:Q", title="Público Efetivo")
    ]
)

# Combinar os dois gráficos em um layer chart
layer_chart = alt.layer(bar_chart, line_chart).resolve_scale(y='independent').properties(
    width=800,
    height=400,
    title="Distribuição do Público Previsto e Efetivo por Hora"
)

st.altair_chart(layer_chart, use_container_width=True)
