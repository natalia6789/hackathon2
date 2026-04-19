import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
from plotly.subplots import make_subplots

st.set_page_config(layout="wide")

# st.title("Хакатон")

# --- Навигация ---
page = st.sidebar.selectbox(
    "Выбери экран",
    ["Бизнес", "Отток", "Поведение", "Рекомендации"]
)

# --- Загрузка данных ---
@st.cache_data
def load_data():
    margin_df = pd.read_csv("category_current_margin.csv")
    categories_df = pd.read_csv("category_current_margin_total.csv")
    categories_no_return_df = pd.read_csv("category_expected_margin_total.csv")
    forecast_df = pd.read_csv("forecast_margin_df_current.csv")
    sankey_auth_df = pd.read_csv('sankey_links_authorized.csv')
    sankey_anon_df = pd.read_csv('sankey_links_anonymous.csv')
    intervals_complete = pd.read_csv("intervals_between_purchases_complete.csv")
    intervals_all = pd.read_csv("intervals_between_purchases_all.csv")
    traffic_df = pd.read_csv("total_margin_by_source.csv")
    weekly_margin_df = pd.read_csv("weekly_margin_analytics.csv")
    activity_df = pd.read_csv("sessions_weekly_stats.csv")
    recommendations_df = pd.read_csv("top10_items_per_segment_no_age.csv")
    male_df = pd.read_csv("male_actual.csv")
    male_df['gender'] = 'M'
    female_df = pd.read_csv("female_actual.csv")
    female_df['gender'] = 'F'

    gender_df = pd.concat([male_df, female_df], ignore_index=True)

    return margin_df, categories_df, categories_no_return_df, forecast_df, sankey_auth_df, sankey_anon_df, intervals_complete, intervals_all, traffic_df, weekly_margin_df, activity_df, recommendations_df, gender_df

margin_df, categories_df, categories_no_return_df, forecast_df, sankey_auth_df, sankey_anon_df, intervals_complete, intervals_all, traffic_df, weekly_margin_df, activity_df, recommendations_df, gender_df = load_data()
categories_no_return_df['margin'] = categories_no_return_df['margin'] 
# --- ЭКРАН БИЗНЕС ---
if page == "Бизнес":
    st.header("Бизнес")

    # безопасный парсинг даты (ВАЖНО)
    margin_df["date"] = pd.to_datetime(
        margin_df["date"],
        utc=True,
        errors="coerce"
    )

    # =========================
    # 🔹 KPI блок
    # =========================

    total_margin = categories_df["margin"].sum()
    total_expected_margin = categories_no_return_df["margin"].sum()
    num_categories = categories_df["category"].nunique()
    avg_margin = categories_df["margin"].mean()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Текущая прибыль", f"{total_margin:,.0f}")
    col2.metric("Категории", num_categories)
    col3.metric("Средняя прибыль", f"{avg_margin:,.0f}")
    col4.metric("Ожидаемая прибыль", f"{total_expected_margin:,.0f}")


    st.divider()



    st.subheader("Топ категорий по прибыли: уже доставленные vs ожидаемые")

# Подготавливаем данные для графика с возвратами
    categories_sorted = categories_df.sort_values(
        by="margin",
        ascending=False
    ).reset_index(drop=True)

    total_margin = categories_sorted["margin"].sum()
    categories_sorted["cumulative_percent"] = (categories_sorted["margin"].cumsum() / total_margin) * 100
    top_80 = categories_sorted[categories_sorted["cumulative_percent"] <= 80].copy()
    top_80["type"] = "Доставленные заказы"

# Подготавливаем данные для графика без возвратов
    categories_no_return_sorted = categories_no_return_df.sort_values(
        by="margin",
        ascending=False
    ).reset_index(drop=True)

    total_margin_no_return = categories_no_return_sorted["margin"].sum()
    categories_no_return_sorted["cumulative_percent"] = (categories_no_return_sorted["margin"].cumsum() / total_margin_no_return) * 100
    top_80_no_return = categories_no_return_sorted[categories_no_return_sorted["cumulative_percent"] <= 80].copy()
    top_80_no_return["type"] = "С учетом ожидаемых заказов"

# Объединяем оба датафрейма
# Нужно убедиться, что категории одинаковые в обоих файлах
    combined_df = pd.concat([top_80, top_80_no_return], ignore_index=True)

# Строим grouped bar chart
    fig = px.bar(
        combined_df,
        x="category",
        y="margin",
        color="type",
        barmode="group",  # группированные столбцы рядом
        title="Категории, которые дают 80% от всей прибыли",
        labels={"margin": "Прибыль (руб)", "category": "Категория", "type": "Тип"},
        text="margin",
        color_discrete_map={
            "Доставленные заказы": "#62aade",  # синий
            "С учетом ожидаемых заказов": "#e87b7b"   # красный
        }
    )

# Настройка внешнего вида
    fig.update_layout(
        xaxis_title="Категория",
        yaxis_title="Прибыль в рублях",
        xaxis={'categoryorder': 'total descending'},  # сортируем по сумме
        height=550,
    # yaxis=dict(
    #     range=[0, combined_df["margin"].max() * 1.15]  # отступ сверху для текста
    # ),
        legend=dict(
            title="Тип данных",
            orientation="h",  # горизонтальная легенда
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )

# Форматируем текст на столбцах
    fig.update_traces(
        texttemplate='%{text:,.0f}',
        textposition='outside',
        textfont=dict(size=10)
    )

    st.plotly_chart(fig, use_container_width=True)



    with st.sidebar:
        st.header("Настройки отображения")
        
        # Выбор гранулярности (применяется ко всем графикам)
        granularity = st.radio(
            "Агрегация по времени:",
            options=["День", "Неделя", "Месяц"],
            horizontal=False,
            key="global_granularity"
        )
        
        st.divider()
        
        # Тумблеры для выбора отображаемых данных
        st.subheader("Отображать на графиках")
        
        show_historical = st.checkbox(
            "Исторические данные",
            value=True,
            key="show_historical"
        )
        
        show_forecast = st.checkbox(
            "Прогноз",
            value=True,
            key="show_forecast"
        )
        
        st.divider()
        
        # Выбор периода времени
        st.subheader("Выбор периода")
        
        min_date = pd.to_datetime(forecast_df['date'].min()).date()
        max_date = pd.to_datetime(forecast_df['date'].max()).date()

        # Опции для быстрого выбора
        period_preset = st.selectbox(
            "Быстрый выбор:",
            options=["Весь период", "Последний месяц", "Последние 3 месяца", "Последний год", "Произвольный период"],
            key="period_preset"
        )
        
        if period_preset == "Произвольный период":
            date_range = st.date_input(
                "Выберите диапазон дат:",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="custom_date_range"
            )
            if len(date_range) == 2:
                start_date, end_date = date_range
            else:
                start_date, end_date = min_date, max_date
        else:
            end_date = max_date
            if period_preset == "Последний месяц":
                start_date = end_date - pd.Timedelta(days=30)
            elif period_preset == "Последние 3 месяца":
                start_date = end_date - pd.Timedelta(days=90)
            elif period_preset == "Последний год":
                start_date = end_date - pd.Timedelta(days=365)
            else:  # Весь период
                start_date = min_date

            st.caption(f"Период: {start_date.strftime('%d.%m.%Y')} — {end_date.strftime('%d.%m.%Y')}")
        
        st.divider()
        
        # Кнопка сброса всех фильтров
        if st.button("Сбросить все фильтры", use_container_width=True):
            st.session_state.period_preset = "Весь период"
            st.session_state.global_granularity = "День"
            st.session_state.show_historical = True
            st.session_state.show_forecast = True
            st.rerun()

    # Функция для фильтрации по дате
    def filter_by_date_range(df, start_date, end_date):
        mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
        return df[mask].copy()

    # Функция для удаления последнего неполного периода из данных
    def remove_last_incomplete_period(df, granularity):
        """Удаляет последний неполный период из данных"""
        if df.empty:
            return df
        
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        
        if granularity == "День":
            # Для дня - оставляем все
            return df
        elif granularity == "Неделя":
            # Находим последнюю полную неделю
            last_date = df['date'].max()
            last_complete_week = last_date - pd.Timedelta(days=7)
            return df[df['date'] <= last_complete_week]
        elif granularity == "Месяц":
            # Оставляем только полные месяцы
            last_date = df['date'].max()
            # Перемещаемся на первый день последнего месяца, затем вычитаем 1 день
            last_complete_month = last_date.replace(day=1) - pd.Timedelta(days=1)
            return df[df['date'] <= last_complete_month]
        else:
            return df

    # Функция для агрегации данных по выбранной гранулярности (одиночная категория)
    def aggregate_by_granularity(df, granularity):
        df = df.copy()
        df = df.dropna(subset=['date'])
        
        if df.empty:
            return pd.DataFrame(columns=['date', 'margin'])
        
        # Преобразуем даты и устанавливаем индекс
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        
        # Выбираем правило агрегации
        if granularity == "Неделя":
            freq = 'W'
        elif granularity == "Месяц":
            freq = 'ME'  # новый стандарт
        else:  # День
            freq = 'D'
        
        # Пробуем разные варианты для месяца (на случай если 'ME' не поддерживается)
        try:
            aggregated = df['margin'].resample(freq).sum().reset_index()
        except:
            if granularity == "Месяц":
                aggregated = df['margin'].resample('M').sum().reset_index()
            else:
                raise
        
        aggregated.columns = ['date', 'margin']
        return aggregated

    # Функция для агрегации с группировкой по категориям
    def aggregate_categories_by_granularity(df, granularity):
        df = df.copy()
        df = df.dropna(subset=['date'])
        
        if df.empty:
            return pd.DataFrame(columns=['date', 'margin', 'category'])
        
        # Преобразуем даты
        df['date'] = pd.to_datetime(df['date'])
        
        # Выбираем правило агрегации
        if granularity == "Неделя":
            freq = 'W'
        elif granularity == "Месяц":
            freq = 'ME'
        else:  # День
            freq = 'D'
        
        # Используем pd.Grouper для группировки по дате и категории
        try:
            result = df.groupby([
                pd.Grouper(key='date', freq=freq),
                'category'
            ])['margin'].sum().reset_index()
        except:
            # Если 'ME' не работает, пробуем 'M'
            if granularity == "Месяц":
                result = df.groupby([
                    pd.Grouper(key='date', freq='M'),
                    'category'
                ])['margin'].sum().reset_index()
            else:
                raise
        
        result.columns = ['date', 'category', 'margin']
        return result

    # Применяем фильтр по дате ко всему датасету
    margin_df_filtered = filter_by_date_range(margin_df, start_date, end_date)

    # Убираем временную зону если она есть
    if margin_df['date'].dt.tz is not None:
        margin_df['date'] = margin_df['date'].dt.tz_localize(None)
        margin_df_filtered = filter_by_date_range(margin_df, start_date, end_date)

    # Подготавливаем forecast_df (колонка с прогнозом называется 'yhat')
    forecast_df_filtered = None
    if 'forecast_df' in globals() or 'forecast_df' in locals():
        # Оставляем только нужные колонки: date, category и yhat
        forecast_df_clean = forecast_df[['date', 'category', 'yhat']].copy()
        forecast_df_clean.columns = ['date', 'category', 'margin']
        forecast_df_clean['date'] = pd.to_datetime(forecast_df_clean['date'])
        
        # Убираем временную зону если она есть
        if forecast_df_clean['date'].dt.tz is not None:
            forecast_df_clean['date'] = forecast_df_clean['date'].dt.tz_localize(None)
        
        forecast_df_filtered = filter_by_date_range(forecast_df_clean, start_date, end_date)

    # Теперь основной контент страницы
    st.subheader("Прибыль по времени")

    # Получаем список всех категорий из ОТФИЛЬТРОВАННЫХ данных
    categories_list = sorted(margin_df_filtered["category"].unique())

    # Выпадающий список для выбора категории
    selected_category = st.selectbox(
        "Выберите категорию:",
        options=categories_list,
        key="margin_category_select"
    )

    # Фильтруем и агрегируем данные по выбранной категории
    category_data = margin_df_filtered[margin_df_filtered["category"] == selected_category].copy()
    category_data = category_data.sort_values("date")

    if not category_data.empty:
        # Применяем агрегацию к историческим данным
        plot_data = aggregate_by_granularity(category_data, granularity)
        
        # Убираем временную зону из дат в plot_data если есть
        if not plot_data.empty and plot_data['date'].dt.tz is not None:
            plot_data['date'] = plot_data['date'].dt.tz_localize(None)
        
        # Удаляем последний неполный период из исторических данных
        plot_data = remove_last_incomplete_period(plot_data, granularity)
        
        # Применяем агрегацию к прогнозным данным
        forecast_plot_data = None
        if show_forecast and forecast_df_filtered is not None and selected_category in forecast_df_filtered["category"].unique():
            forecast_cat_data = forecast_df_filtered[forecast_df_filtered["category"] == selected_category].copy()
            forecast_plot_data = aggregate_by_granularity(forecast_cat_data, granularity)
            
            # Убираем временную зону из дат в forecast_plot_data если есть
            if forecast_plot_data is not None and not forecast_plot_data.empty:
                if forecast_plot_data['date'].dt.tz is not None:
                    forecast_plot_data['date'] = forecast_plot_data['date'].dt.tz_localize(None)
                
                # Удаляем последний неполный период из прогнозных данных
                forecast_plot_data = remove_last_incomplete_period(forecast_plot_data, granularity)
        
        if not plot_data.empty:
            # Создаем комбинированный DataFrame в зависимости от выбранных опций
            combined_data = pd.DataFrame()
            
            if show_historical:
                plot_data_indexed = plot_data.set_index("date")[["margin"]]
                plot_data_indexed.columns = ["История"]
                combined_data = plot_data_indexed
            
            if show_forecast and forecast_plot_data is not None and not forecast_plot_data.empty:
                forecast_indexed = forecast_plot_data.set_index("date")[["margin"]]
                forecast_indexed.columns = ["Прогноз"]
                if combined_data.empty:
                    combined_data = forecast_indexed
                else:
                    combined_data = combined_data.join(forecast_indexed, how='outer')
            
            if not combined_data.empty:
                st.line_chart(
                    combined_data,
                    use_container_width=True
                )
                
                # Формируем текст подписи
                caption_text = f"Данные за период: {start_date.strftime('%d.%m.%Y')} — {end_date.strftime('%d.%m.%Y')} | Агрегация: {granularity}"
                if show_historical and show_forecast:
                    caption_text += " | 🔵 История | 🔴 Прогноз"
                elif show_historical:
                    caption_text += " | 🔵 Только история"
                elif show_forecast:
                    caption_text += " | 🔴 Только прогноз"
                st.caption(caption_text)

                if show_forecast and forecast_df_clean is not None:
                    # --- ГОДОВЫЕ МЕТРИКИ ---
                    st.subheader("Годовые показатели по категории")
                    
                    # Исторические данные за последний год
                    last_historical_date = category_data['date'].max()
                    forecast_cat_full = forecast_df_clean[forecast_df_clean['category'] == selected_category].copy()
                    year_ago = last_historical_date - pd.Timedelta(days=365)
                    historical_last_year = category_data[
                        (category_data['date'] >= year_ago) & 
                        (category_data['date'] <= last_historical_date)
                    ]
                    historical_sum = historical_last_year['margin'].sum()
                    
                    # Прогноз на следующий год
                    next_year_end = last_historical_date + pd.Timedelta(days=365)
                    forecast_next_year = forecast_cat_full[
                        (forecast_cat_full['date'] > last_historical_date) & 
                        (forecast_cat_full['date'] <= next_year_end)
                    ]
                    forecast_sum = forecast_next_year['margin'].sum()
                    
                    # Расчет процента изменения
                    if historical_sum > 0:
                        yearly_pct_change = ((forecast_sum - historical_sum) / historical_sum) * 100
                    else:
                        yearly_pct_change = 0
                    
                    col3, col4 = st.columns(2)
                    
                    with col3:
                        st.metric(
                            label=f"Суммарная прибыль за последний год ({year_ago.strftime('%d.%m.%Y')} — {last_historical_date.strftime('%d.%m.%Y')})",
                            value=f"{historical_sum:,.0f} ₽".replace(",", " "),
                            delta=None
                        )
                    
                    with col4:
                        st.metric(
                            label=f"Прогноз на следующий год ({last_historical_date.strftime('%d.%m.%Y')} — {next_year_end.strftime('%d.%m.%Y')})",
                            value=f"{forecast_sum:,.0f} ₽".replace(",", " "),
                            delta=f"{yearly_pct_change:+.1f}%"
                        )

                    st.divider()
                    st.subheader("Годовые показатели по всем категориям")
                    last_historical_date_all = margin_df['date'].max()
                    year_ago_all = last_historical_date_all - pd.Timedelta(days=365)

                    historical_last_year_all = margin_df[
                        (margin_df['date'] >= year_ago_all) & 
                        (margin_df['date'] <= last_historical_date_all)
                    ]
                    historical_sum_all = historical_last_year_all['margin'].sum()

                    # Прогноз на следующий год по всем категориям
                    next_year_end_all = last_historical_date_all + pd.Timedelta(days=365)

                    # Суммируем прогнозы по всем категориям
                    forecast_next_year_all = forecast_df_clean[
                        (forecast_df_clean['date'] > last_historical_date_all) & 
                        (forecast_df_clean['date'] <= next_year_end_all)
                    ]
                    forecast_sum_all = forecast_next_year_all['margin'].sum()

                    # Расчет процента изменения
                    if historical_sum_all > 0:
                        yearly_pct_change_all = ((forecast_sum_all - historical_sum_all) / historical_sum_all) * 100
                    else:
                        yearly_pct_change_all = 0

                    col_all1, col_all2 = st.columns(2)

                    with col_all1:
                        st.metric(
                            label=f"Суммарная прибыль за последний год ({year_ago_all.strftime('%d.%m.%Y')} — {last_historical_date_all.strftime('%d.%m.%Y')})",
                            value=f"{historical_sum_all:,.0f} ₽".replace(",", " "),
                            delta=None
                        )

                    with col_all2:
                        st.metric(
                            label=f"Прогноз на следующий год ({last_historical_date_all.strftime('%d.%m.%Y')} — {next_year_end_all.strftime('%d.%m.%Y')})",
                            value=f"{forecast_sum_all:,.0f} ₽".replace(",", " "),
                            delta=f"{yearly_pct_change_all:+.1f}%"
                        )
                    st.divider()    
                else:
                    st.info("Нет прогнозных данных для выбранной категории")
            else:
                st.info("Выберите хотя бы один тип данных для отображения")
        else:
            st.info("Нет данных для отображения с выбранной агрегацией")
    else:
        st.info("Нет данных для выбранной категории в указанном периоде")

    st.subheader("Сравнение категорий по прибыли")
    # Мультиселект для сравнения нескольких категорий
    compare_categories = st.multiselect(
        "Сравнить категории (выберите 2-5):",
        options=sorted(margin_df_filtered["category"].unique()),
        default=sorted(margin_df_filtered["category"].unique())[:min(3, len(margin_df_filtered["category"].unique()))],
        key="compare_multiselect"
    )

    if len(compare_categories) >= 2:
        filtered_df = margin_df_filtered[margin_df_filtered["category"].isin(compare_categories)]
        aggregated_df = aggregate_categories_by_granularity(filtered_df, granularity)
        
        if not aggregated_df.empty:
            # Убираем временную зону если есть
            if aggregated_df['date'].dt.tz is not None:
                aggregated_df['date'] = aggregated_df['date'].dt.tz_localize(None)
            
            # Удаляем последний неполный период из исторических данных
            aggregated_df = remove_last_incomplete_period(aggregated_df, granularity)
            
            # Создаем pivot table для исторических данных
            pivot = pd.DataFrame()
            
            if show_historical and not aggregated_df.empty:
                pivot = aggregated_df.pivot_table(
                    index="date",
                    columns="category",
                    values="margin",
                    aggfunc="sum"
                )
            
            # Добавляем прогнозные данные если нужно
            if show_forecast and forecast_df_filtered is not None:
                forecast_filtered = forecast_df_filtered[forecast_df_filtered["category"].isin(compare_categories)]
                if not forecast_filtered.empty:
                    forecast_aggregated = aggregate_categories_by_granularity(forecast_filtered, granularity)
                    
                    # Убираем временную зону если есть
                    if forecast_aggregated['date'].dt.tz is not None:
                        forecast_aggregated['date'] = forecast_aggregated['date'].dt.tz_localize(None)
                    
                    # Удаляем последний неполный период из прогнозных данных
                    forecast_aggregated = remove_last_incomplete_period(forecast_aggregated, granularity)
                    
                    if not forecast_aggregated.empty:
                        forecast_pivot = forecast_aggregated.pivot_table(
                            index="date",
                            columns="category",
                            values="margin",
                            aggfunc="sum"
                        )
                        # Добавляем суффикс '_прогноз' к колонкам
                        forecast_pivot.columns = [f"{col}_прогноз" for col in forecast_pivot.columns]
                        
                        # Объединяем с историческими данными
                        if pivot.empty:
                            pivot = forecast_pivot
                        else:
                            pivot = pivot.join(forecast_pivot, how='outer')
            
            if not pivot.empty:
                st.line_chart(pivot, use_container_width=True)
                
                # Формируем текст подписи
                caption_text = f"Сравнение динамики разных категорий | Период: {start_date.strftime('%d.%m.%Y')} — {end_date.strftime('%d.%m.%Y')} | Агрегация: {granularity}"
                if show_historical and show_forecast:
                    caption_text += " | 🔵 История | 🔴 Прогноз"
                elif show_historical:
                    caption_text += " | 🔵 Только история"
                elif show_forecast:
                    caption_text += " | 🔴 Только прогноз"
                st.caption(caption_text)
            else:
                st.info("Выберите хотя бы один тип данных для отображения")
        else:
            st.info("Нет данных для выбранных категорий в указанном периоде")
            
    elif len(compare_categories) == 1:
        st.info("Выберите ещё хотя бы одну категорию для сравнения")
    else:
        st.info("Выберите 2-5 категорий для сравнения")


# --- ЭКРАН КЛИЕНТЫ ---
elif page == "Отток":
    st.header("Отток")
    # Заголовок
    # st.subheader("🎯 Анализ риска оттока клиентов")

    # Загрузка данных
    @st.cache_data
    def load_churn_data():
        result_table = pd.read_csv(
            "customer_churn_predictions.csv",
            parse_dates=["created_at"]
        )
        return result_table

    result_table = load_churn_data()

    # Разделение на группы
    loyal = result_table[result_table["is_loyal"] == 1].copy()
    not_loyal = result_table[result_table["is_loyal"] == 0].copy()

    # Целевая доля клиентов для вмешательства
    target_share = 0.30

    # Индивидуальные thresholds для каждой группы
    loyal_threshold = loyal["probability_churn"].quantile(1 - target_share)
    not_loyal_threshold = not_loyal["probability_churn"].quantile(1 - target_share)

    # Процент клиентов в зоне риска
    loyal_high_risk_share = ((loyal["probability_churn"] >= loyal_threshold).mean() * 100)
    not_loyal_high_risk_share = ((not_loyal["probability_churn"] >= not_loyal_threshold).mean() * 100)
    all_high_risk_share = (
        ((loyal["probability_churn"] >= loyal_threshold).sum() +
        (not_loyal["probability_churn"] >= not_loyal_threshold).sum()) / len(result_table) * 100
    )

    st.markdown("### Ключевые показатели")
    col1, col2 = st.columns(2)
    col1.metric("Порог (лояльные)", f"{loyal_threshold*100:.3f}%")
    col2.metric("Порог (нелояльные)", f"{not_loyal_threshold*100:.3f}%")
    

    col1, col2 = st.columns(2)
    col1.metric("Лояльные в зоне риска", f"{loyal_high_risk_share:.1f}%")
    col2.metric("Нелояльные в зоне риска", f"{not_loyal_high_risk_share:.1f}%")
    

    st.divider()


    st.markdown("### Анализ риска оттока клиентов")

    fig1 = go.Figure()

    # Гистограмма для лояльных
    fig1.add_trace(go.Histogram(
        x=loyal["probability_churn"],
        name="Лояльные клиенты",
        opacity=0.6,
        marker_color="blue",
        nbinsx=40,
        autobinx=False
    ))

    # Гистограмма для нелояльных
    fig1.add_trace(go.Histogram(
        x=not_loyal["probability_churn"],
        name="Нелояльные клиенты",
        opacity=0.6,
        marker_color="red",
        nbinsx=40,
        autobinx=False
    ))

    # Вертикальные линии порогов
    fig1.add_vline(
        x=loyal_threshold,
        line_dash="dash",
        line_color="blue",
        line_width=2,
        annotation_text=f"Порог лояльных = {loyal_threshold:.2f}",
        annotation_position="top"
    )

    fig1.add_vline(
        x=not_loyal_threshold,
        line_dash="dash",
        line_color="red",
        line_width=2,
        annotation_text=f"Порог нелояльных = {not_loyal_threshold:.2f}",
        annotation_position="top"
    )

    fig1.update_layout(
        title="Распределение вероятности оттока",
        xaxis_title="Вероятность оттока",
        yaxis_title="Количество клиентов",
        barmode="overlay",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="center",
            x=0.5
        ),
        height=700
    )

    st.plotly_chart(fig1, use_container_width=True)

    # =========================
    # 2. КУМУЛЯТИВНОЕ РАСПРЕДЕЛЕНИЕ (Plotly)
    # =========================
    st.markdown("### Распределение риска оттока")

    # Сортируем вероятности
    loyal_probs = np.sort(loyal["probability_churn"].values)
    not_loyal_probs = np.sort(not_loyal["probability_churn"].values)

    # Кумулятивные доли
    loyal_cum_share = np.arange(1, len(loyal_probs) + 1) / len(loyal_probs)
    not_loyal_cum_share = np.arange(1, len(not_loyal_probs) + 1) / len(not_loyal_probs)

 # Сортируем вероятности
    loyal_probs = np.sort(loyal["probability_churn"].values)
    not_loyal_probs = np.sort(not_loyal["probability_churn"].values)

    # Кумулятивные доли
    loyal_cum_share = np.arange(1, len(loyal_probs) + 1) / len(loyal_probs)
    not_loyal_cum_share = np.arange(1, len(not_loyal_probs) + 1) / len(not_loyal_probs)

        # Находим индексы порогов
    loyal_threshold_idx = np.searchsorted(loyal_probs, loyal_threshold)
    not_loyal_threshold_idx = np.searchsorted(not_loyal_probs, not_loyal_threshold)

    fig2 = go.Figure()

    # ==========================================
    # ЛОЯЛЬНЫЕ КЛИЕНТЫ
    # ==========================================
    # Часть ДО порога (левее)
    if loyal_threshold_idx > 0:
        fig2.add_trace(go.Scatter(
            x=loyal_probs[:loyal_threshold_idx + 1],
            y=loyal_cum_share[:loyal_threshold_idx + 1],
            mode="lines",
            name="Лояльные (до порога)",
            line=dict(color="#68ACFF", width=3),  # зелёный
            showlegend=True
        ))

    # Часть ПОСЛЕ порога (правее)
    if loyal_threshold_idx < len(loyal_probs):
        fig2.add_trace(go.Scatter(
            x=loyal_probs[loyal_threshold_idx:],
            y=loyal_cum_share[loyal_threshold_idx:],
            mode="lines",
            name="Лояльные (после порога)",
            line=dict(color="#004E9B", width=3),  # тёмно-зелёный
            showlegend=True
        ))

    # ==========================================
    # НЕЛОЯЛЬНЫЕ КЛИЕНТЫ
    # ==========================================
    # Часть ДО порога (левее)
    if not_loyal_threshold_idx > 0:
        fig2.add_trace(go.Scatter(
            x=not_loyal_probs[:not_loyal_threshold_idx + 1],
            y=not_loyal_cum_share[:not_loyal_threshold_idx + 1],
            mode="lines",
            name="Нелояльные (до порога)",
            line=dict(color="#FF7676", width=3),  # оранжевый
            showlegend=True
        ))

    # Часть ПОСЛЕ порога (правее)
    if not_loyal_threshold_idx < len(not_loyal_probs):
        fig2.add_trace(go.Scatter(
            x=not_loyal_probs[not_loyal_threshold_idx:],
            y=not_loyal_cum_share[not_loyal_threshold_idx:],
            mode="lines",
            name="Нелояльные (после порога)",
            line=dict(color="#B50000", width=3),  # тёмно-красный
            showlegend=True
        ))


    # Вертикальные линии порогов
    fig2.add_vline(
        x=loyal_threshold,
        line_dash="dash",
        line_color="blue",
        line_width=2,
        annotation_text=f"Порог лояльных = {loyal_threshold:.2f}",
        annotation_position="top"
    )

    fig2.add_vline(
        x=not_loyal_threshold,
        line_dash="dash",
        line_color="red",
        line_width=2,
        annotation_text=f"Порог нелояльных = {not_loyal_threshold:.2f}",
        annotation_position="top"
    )

    fig2.update_layout(
        # title="Кумулятивное распределение риска оттока",
        xaxis_title="Вероятность оттока",
        yaxis_title="Накопленная доля клиентов",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="center",
            x=0.5
        ),
        height=700
    )

    st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    st.subheader("🔍 Поиск пользователя")

    # Поля для поиска
    col_search1, col_search2 = st.columns([3, 1])

    with col_search1:
        user_id_input = st.number_input(
            "Введите ID пользователя:",
            min_value=0,
            step=1,
            format="%d",
            key="search_user_id"
        )

    with col_search2:
        search_button = st.button(
            "🔍 Найти пользователя",
            use_container_width=True,
            key="search_user_button"
        )

    # Функция поиска пользователя
    def find_customer_info(user_id, result_table):
        """Поиск информации о пользователе"""
        customer = result_table[result_table["user_id"] == user_id]
        
        if customer.empty:
            return None
        return customer.iloc[0]

    # Поиск при нажатии кнопки
    if search_button and user_id_input > 0:
        customer = find_customer_info(user_id_input, result_table)
        
        if customer is not None:
            st.success(f"Пользователь {user_id_input} найден")
            
            # ==========================================
            # 1. ОБЩАЯ ИНФОРМАЦИЯ
            # ==========================================
            st.markdown("### Общая информация")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("User ID", customer['user_id'])
            with col2:
                st.metric("Возраст", f"{customer['age']} лет")
            with col3:
                st.metric("Страна", customer['country'])
            with col4:
                is_loyal = customer['is_loyal']
                loyal_text = "✅ ДА" if is_loyal else "❌ НЕТ"
                st.metric("Лояльный клиент", loyal_text)
            st.divider()
            
            # ==========================================
            # 2. ТЕКУЩИЙ ЗАКАЗ
            # ==========================================
            st.markdown("### Последний заказ")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Дата последнего заказа", customer['created_at'].strftime('%d.%m.%Y'))
            with col2:
                st.metric("Количество товаров", customer['total_items'])
            with col3:
                st.metric("Дней с последнего заказа", f"{customer['days_since_order']:.0f}")
            
            st.divider()
            
            # ==========================================
            # 3. ПРЕДЫДУЩИЕ ЗАКАЗЫ (ИСТОРИЯ)
            # ==========================================
            st.markdown("### Статистика заказов (без последнего)")
            
            user_orders_before = customer['user_orders_before']
            
            if user_orders_before > 0:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Количество прошлых заказов", f"{user_orders_before}")
                with col2:
                    st.metric("Среднее число товаров", f"{customer['user_avg_items_before']:.2f}")
                with col3:
                    st.metric("Средняя прибыль", f"{customer['user_avg_margin_before']:.2f} ₽")
    
            
            else:
                st.info("**Это первый заказ пользователя!** Нет данных о предыдущих заказах.")
            
            st.divider()
            
            # ==========================================
            # РИСК ОТТОКА (особое внимание)
            # ==========================================
            st.markdown("### Риск оттока")
            
            prob_churn = customer['probability_churn']
            need_intervention = customer['need_intervention']
            
            # Цветовая индикация вероятности оттока
            if prob_churn < 0.3:
                churn_color = "green"
                churn_status = "🟢 Низкий"
            elif prob_churn < 0.7:
                churn_color = "orange"
                churn_status = "🟡 Средний"
            else:
                churn_color = "red"
                churn_status = "🔴 Высокий"
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(
                    f"""
                    <div style='background-color: {churn_color}20; padding: 20px; border-radius: 10px; text-align: center;'>
                        <h4 style='color: {churn_color}; margin: 0;'>Вероятность оттока</h4>
                        <p style='font-size: 36px; font-weight: bold; color: {churn_color}; margin: 10px 0;'>{prob_churn * 100:.1f}%</p>
                        <p style='margin: 0;'>Статус: {churn_status}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            with col2:
                # Нужно ли вмешательство с цветом
                if need_intervention == 1:
                    intervention_color = "red"
                    intervention_text = "🔴 ТРЕБУЕТСЯ ВМЕШАТЕЛЬСТВО"
                    intervention_bg = "#ff000020"
                else:
                    intervention_color = "green"
                    intervention_text = "🟢 ВМЕШАТЕЛЬСТВО НЕ ТРЕБУЕТСЯ"
                    intervention_bg = "#00ff0020"
                
                st.markdown(
                    f"""
                    <div style='background-color: {intervention_bg}; padding: 20px; border-radius: 10px; text-align: center;'>
                        <h4 style='color: {intervention_color}; margin: 0;'>Статус</h4>
                        <p style='font-size: 20px; font-weight: bold; color: {intervention_color}; margin: 10px 0;'>{intervention_text}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            st.divider()
            
            
        else:
            st.error(f"❌ Пользователь с ID {user_id_input} не найден")
            st.info("Попробуйте ввести другой ID пользователя")

    elif search_button and user_id_input == 0:
        st.warning("⚠️ Введите ID пользователя (число больше 0)")
    
# --- ЭКРАН ПОВЕДЕНИЕ ---
elif page == "Поведение":
    st.header("Поведение пользователей")
    
    # Функция для создания Sankey диаграммы
    def create_sankey(df):
        # Задаем желаемый порядок узлов
        desired_order = ['home', 'department', 'product', 'cart', 'purchase']
        
        # Получаем все уникальные узлы из данных
        all_nodes_set = set(df['source'].unique()) | set(df['target'].unique())
        
        # Сортируем узлы согласно желаемому порядку
        all_nodes = []
        for node in desired_order:
            if node in all_nodes_set:
                all_nodes.append(node)
        
        # Добавляем остальные узлы, которых нет в desired_order (если есть)
        for node in all_nodes_set:
            if node not in all_nodes:
                all_nodes.append(node)
        
        # Создаем словарь для маппинга названий в индексы
        node_dict = {node: i for i, node in enumerate(all_nodes)}
        
        source_indices = [node_dict[src] for src in df['source']]
        target_indices = [node_dict[tgt] for tgt in df['target']]
        values = df['value'].tolist()
        
        
        colors = [
            'rgba(31, 119, 180, 0.8)',
            'rgba(255, 127, 14, 0.8)',
            'rgba(44, 160, 44, 0.8)',
            'rgba(214, 39, 40, 0.8)',
            'rgba(148, 103, 189, 0.8)',
            'rgba(140, 86, 75, 0.8)',
            'rgba(227, 119, 194, 0.8)',
            'rgba(127, 127, 127, 0.8)',
            'rgba(188, 189, 34, 0.8)',
            'rgba(23, 190, 207, 0.8)'
        ]
        
        node_colors = [colors[i % len(colors)] for i in range(len(all_nodes))]
        
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=all_nodes,
                color=node_colors
            ),
            link=dict(
                source=source_indices,
                target=target_indices,
                value=values,
                hovertemplate='%{source.label} → %{target.label}<br>Вероятность: %{value:.2%}<extra></extra>'
            )
        )])
        
        fig.update_layout(
            font=dict(size=12),
            height=500,
            paper_bgcolor='white',
            plot_bgcolor='white'
        )
        
        return fig

    # --- АВТОРИЗОВАННЫЕ ПОЛЬЗОВАТЕЛИ ---
    st.subheader("Авторизованные пользователи")
    st.caption("Вероятности переходов между категориями")
    
    fig_auth = create_sankey(sankey_auth_df)
    st.plotly_chart(fig_auth, use_container_width=True)
    
    # Статистика для авторизованных
    st.write("**Топ-3 вероятных переходов:**")
    top_auth = sankey_auth_df.nlargest(3, 'value')[['source', 'target', 'value']]

    col_a1, col_a2, col_a3 = st.columns(3)

    for i, (col, (_, row)) in enumerate(zip([col_a1, col_a2, col_a3], top_auth.iterrows())):
        with col:
            st.markdown(
                f"<div style='text-align: center; padding: 15px; border-radius: 8px; "
                f"border: 1px solid #000000; background-color: #ffffff;'>"
                f"<div style='font-size: 14px; color: #666666; margin-bottom: 8px;'>#{i+1}</div>"
                f"<div style='font-size: 16px; color: #000000; margin-bottom: 8px;'>{row['source']} → {row['target']}</div>"
                f"<div style='font-size: 22px; font-weight: bold; color: #000000;'>{row['value']:.1%}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
    
    st.divider()
    
    # --- НЕАВТОРИЗОВАННЫЕ ПОЛЬЗОВАТЕЛИ ---
    st.subheader("Неавторизованные пользователи")
    st.caption("Вероятности переходов между категориями")
    
    fig_anon = create_sankey(sankey_anon_df)
    st.plotly_chart(fig_anon, use_container_width=True)
    
    # Статистика для неавторизованных
    st.write("**Топ-3 вероятных переходов:**")
    top_anon = sankey_anon_df.nlargest(3, 'value')[['source', 'target', 'value']]

    col_u1, col_u2, col_u3 = st.columns(3)

    for i, (col, (_, row)) in enumerate(zip([col_u1, col_u2, col_u3], top_anon.iterrows())):
        with col:
            st.markdown(
                f"<div style='text-align: center; padding: 15px; border-radius: 8px; "
                f"border: 1px solid #000000; background-color: #ffffff;'>"
                f"<div style='font-size: 14px; color: #666666; margin-bottom: 8px;'>#{i+1}</div>"
                f"<div style='font-size: 16px; color: #000000; margin-bottom: 8px;'>{row['source']} → {row['target']}</div>"
                f"<div style='font-size: 22px; font-weight: bold; color: #000000;'>{row['value']:.1%}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    st.subheader("Распределение прибыли по источникам трафика")

    # Создаем две колонки
    col_pie, col_info = st.columns([1.5, 1])

    with col_pie:
        # Создаем pie chart через Plotly
        fig_pie = go.Figure(data=[go.Pie(
            labels=traffic_df['traffic_source'],
            values=traffic_df['absolute_margin'],
            textinfo='percent',  # показываем только проценты на графике
            textposition='inside',
            hole=0.0,
            marker=dict(
                colors=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'],
                line=dict(color='white', width=1.5)
            ),
            hovertemplate='<b>%{label}</b><br>Прибыль: %{value:,.0f} ₽<br>Доля: %{percent}<extra></extra>',
            sort=False  # сохраняем порядок из данных
        )])
        
        fig_pie.update_layout(
            title="Распределение абсолютной прибыли по источникам",
            height=400,
            showlegend=False,  # убираем легенду, так как информация будет справа
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(size=12),
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_info:
        st.write("**Источники трафика**")
        
        # Сортируем по убыванию маржи
        display_df = traffic_df.sort_values('absolute_margin', ascending=False).copy()
        
        # Рассчитываем проценты
        total = display_df['absolute_margin'].sum()
        display_df['percentage'] = (display_df['absolute_margin'] / total * 100).round(1)
        
        # Цвета для источников
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        
        # Выводим каждый источник отдельной строкой
        for i, (_, row) in enumerate(display_df.iterrows()):
            color = colors[i % len(colors)]
            margin_formatted = f"{row['absolute_margin']:,.0f}".replace(",", " ")
            
            st.markdown(
                f"<div style='display: flex; align-items: center; margin-bottom: 15px;'>"
                f"<div style='width: 12px; height: 12px; background-color: {color}; "
                f"border-radius: 3px; margin-right: 10px;'></div>"
                f"<div style='flex: 1;'>"
                f"<div style='font-weight: bold;'>{row['traffic_source']}</div>"
                f"<div style='font-size: 12px; color: #666;'>{margin_formatted} ₽</div>"
                f"</div>"
                f"<div style='font-size: 18px; font-weight: bold;'>{row['percentage']:.1f}%</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        
        # Итого
        total_formatted = f"{total:,.0f}".replace(",", " ")
        st.divider()
        st.markdown(
            f"<div style='display: flex; justify-content: space-between;'>"
            f"<span style='font-weight: bold;'>Итого</span>"
            f"<span style='font-weight: bold;'>{total_formatted} ₽</span>"
            f"</div>",
            unsafe_allow_html=True
        )


### НЕДЕЛЬНАЯ МАРЖА ПО ИСТОЧНИКАМ
    weekly_margin_df['created_at'] = pd.to_datetime(weekly_margin_df['created_at'])
    weekly_margin_df = weekly_margin_df.rename(columns={
        'created_at': 'date',
        'traffic_source': 'source',
        'smoothed_margin': 'margin'
    })
    
    # Убираем временную зону если есть
    if weekly_margin_df['date'].dt.tz is not None:
        weekly_margin_df['date'] = weekly_margin_df['date'].dt.tz_localize(None)
    
    # Боковое меню с настройками
    with st.sidebar:
        st.header("Настройки отображения")
        
        # Выбор гранулярности
        granularity = st.radio(
            "Агрегация по времени:",
            options=["Неделя", "Месяц"],
            horizontal=False,
            key="behavior_granularity"
        )
        
        st.divider()
        
        # # Выбор периода времени
        # st.subheader("Выбор периода")
        
        # min_date = weekly_margin_df['date'].min().date()
        # max_date = weekly_margin_df['date'].max().date()
        
        # period_preset = st.selectbox(
        #     "Быстрый выбор:",
        #     options=["Весь период", "Последний месяц", "Последние 3 месяца", "Последний год", "Произвольный период"],
        #     key="behavior_period_preset"
        # )
        
        # if period_preset == "Произвольный период":
        #     date_range = st.date_input(
        #         "Выберите диапазон дат:",
        #         value=(min_date, max_date),
        #         min_value=min_date,
        #         max_value=max_date,
        #         key="behavior_custom_date_range"
        #     )
        #     if len(date_range) == 2:
        #         start_date, end_date = date_range
        #     else:
        #         start_date, end_date = min_date, max_date
        # else:
        #     end_date = max_date
        #     if period_preset == "Последний месяц":
        #         start_date = end_date - pd.Timedelta(days=30)
        #     elif period_preset == "Последние 3 месяца":
        #         start_date = end_date - pd.Timedelta(days=90)
        #     elif period_preset == "Последний год":
        #         start_date = end_date - pd.Timedelta(days=365)
        #     else:
        #         start_date = min_date
            
        #     st.caption(f"Период: {start_date.strftime('%d.%m.%Y')} — {end_date.strftime('%d.%m.%Y')}")
        
        # st.divider()
        
        # Кнопка сброса
        if st.button("Сбросить все фильтры", use_container_width=True):
            st.session_state.behavior_period_preset = "Весь период"
            st.session_state.behavior_granularity = "Неделя"
            st.rerun()
    
    # Функция для фильтрации по дате
    def filter_by_date_range(df, start_date, end_date):
        mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
        return df[mask].copy()
    
    def aggregate_source_by_granularity(df, granularity):
        df = df.copy()
        df = df.dropna(subset=['date', 'margin'])
        
        if df.empty:
            return pd.DataFrame(columns=['date', 'margin', 'source'])
        
        result_dfs = []
        
        for source in df['source'].unique():
            source_df = df[df['source'] == source].copy()
            source_df = source_df.set_index('date')
            
            if granularity == "Неделя":
                agg = source_df['margin'].resample('W').mean()
            elif granularity == "Месяц":
                # Используем 'ME' вместо 'M' (совместимость с новыми версиями pandas)
                try:
                    agg = source_df['margin'].resample('ME').mean()
                except:
                    # Если 'ME' не работает, пробуем 'M' (для старых версий)
                    agg = source_df['margin'].resample('M').mean()
            else:  # День
                agg = source_df['margin'].resample('D').mean()
            
            agg_df = agg.reset_index()
            agg_df['source'] = source
            result_dfs.append(agg_df)
        
        if result_dfs:
            result = pd.concat(result_dfs, ignore_index=True)
            result.columns = ['date', 'margin', 'source']
            return result
        else:
            return pd.DataFrame(columns=['date', 'margin', 'source'])
    
    # Применяем фильтр по дате
    # weekly_margin_filtered = filter_by_date_range(weekly_margin_df, start_date, end_date)
    # weekly_margin_filtered = filter_by_date_range(weekly_margin_df)
    weekly_margin_filtered = weekly_margin_df
    
    # --- GRAFIK MARZHI PO ISTOCHNIKAM ---
    st.subheader("Динамика сглаженной прибыли по источникам трафика")
    
    # Получаем список источников
    sources_list = sorted(weekly_margin_filtered['source'].unique())
    
    # Выпадающий список для выбора источника
    selected_source = st.selectbox(
        "Выберите источник трафика:",
        options=sources_list,
        key="source_select"
    )
    
    # Фильтруем данные по выбранному источнику
    source_data = weekly_margin_filtered[weekly_margin_filtered['source'] == selected_source].copy()
    source_data = source_data.sort_values("date")
    
    if not source_data.empty:
        # Применяем агрегацию
        plot_data = aggregate_source_by_granularity(source_data, granularity)
        plot_data = plot_data[plot_data['source'] == selected_source]
        
        if not plot_data.empty:
            # Используем st.line_chart вместо Plotly для единого стиля
            chart_data = plot_data.set_index('date')[['margin']]
            chart_data.columns = [selected_source]
            
            st.line_chart(
                chart_data,
                use_container_width=True
            )
            
            # Статистика
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Средняя прибыль", f"{plot_data['margin'].mean():,.0f} ₽")
            with col2:
                st.metric("Максимальная прибыль", f"{plot_data['margin'].max():,.0f} ₽")
            with col3:
                st.metric("Минимальная прибыль", f"{plot_data['margin'].min():,.0f} ₽")
            
            # st.caption(f"Данные за период: {start_date.strftime('%d.%m.%Y')} — {end_date.strftime('%d.%m.%Y')} | Агрегация: {granularity}")
        else:
            st.info("Нет данных для отображения с выбранной агрегацией")
    else:
        st.info("Нет данных для выбранного источника в указанном периоде")
    
    st.divider()
    
    # --- SRAVNENIE ISTOCHNIKOV ---
    st.subheader("Сравнение источников трафика")
    
    compare_sources = st.multiselect(
        "Сравнить источники (выберите 2-5):",
        options=sources_list,
        default=sources_list[:min(3, len(sources_list))],
        key="compare_sources_multiselect"
    )
    
    if len(compare_sources) >= 2:
        filtered_df = weekly_margin_filtered[weekly_margin_filtered['source'].isin(compare_sources)]
        aggregated_df = aggregate_source_by_granularity(filtered_df, granularity)
        
        if not aggregated_df.empty:
            # Создаем pivot table для st.line_chart
            pivot = aggregated_df.pivot_table(
                index='date',
                columns='source',
                values='margin',
                aggfunc='mean'
            )
            
            st.line_chart(
                pivot,
                use_container_width=True
            )
            
            # st.caption(f"Сравнение источников | Период: {start_date.strftime('%d.%m.%Y')} — {end_date.strftime('%d.%m.%Y')} | Агрегация: {granularity}")
        else:
            st.info("Нет данных для выбранных источников в указанном периоде")
            
    elif len(compare_sources) == 1:
        st.info("Выберите ещё хотя бы один источник для сравнения")
    else:
        st.info("Выберите 2-5 источников для сравнения")
    
    st.divider()

    st.subheader("Динамика активности пользователей")
    st.caption("Количество действий по датам")
    activity_df['date'] = pd.to_datetime(activity_df['date'])

    # Убираем временную зону если есть
    if activity_df['date'].dt.tz is not None:
        activity_df['date'] = activity_df['date'].dt.tz_localize(None)

    # Функция для агрегации активности по выбранной гранулярности
    def aggregate_activity_by_granularity(df, granularity):
        df = df.copy()
        df = df.dropna(subset=['date', 'weekly_sessions'])
        
        if df.empty:
            return pd.DataFrame(columns=['date', 'weekly_sessions'])
        
        df = df.set_index('date')
        
        if granularity == "Неделя":
            aggregated = df['weekly_sessions'].resample('W').sum().reset_index()
        elif granularity == "Месяц":
            aggregated = df['weekly_sessions'].resample('ME').sum().reset_index()
        else:  # День
            aggregated = df['weekly_sessions'].resample('D').sum().reset_index()
        
        aggregated.columns = ['date', 'weekly_sessions']
        return aggregated

    # Применяем фильтр по дате (используем те же start_date и end_date из бокового меню)
    # activity_filtered = filter_by_date_range(activity_df, start_date, end_date)
    activity_filtered = activity_df

    if not activity_filtered.empty:
        # Применяем агрегацию
        activity_plot = aggregate_activity_by_granularity(activity_filtered, granularity)
        
        if not activity_plot.empty:
            # Создаем красивый график через Plotly
            fig_activity = go.Figure()
            
            fig_activity.add_trace(go.Scatter(
                x=activity_plot['date'],
                y=activity_plot['weekly_sessions'],
                mode='lines+markers',
                name='Активность',
                line=dict(width=3, color='#2ca02c'),
                marker=dict(size=6, color='#2ca02c'),
                fill='tozeroy',
                fillcolor='rgba(44, 160, 44, 0.1)',
                hovertemplate='<b>%{x|%d.%m.%Y}</b><br>Действий: %{y:,.0f}<extra></extra>'
            ))
            
            fig_activity.update_layout(
                # title="Динамика активности пользователей",
                xaxis_title="Дата",
                yaxis_title="Количество действий",
                height=450,
                hovermode='x unified',
                plot_bgcolor='white',
                paper_bgcolor='white',
                showlegend=False
            )
            
            fig_activity.update_xaxes(
                showgrid=False,
                tickformat='%d.%m.%Y'
            )
            
            fig_activity.update_yaxes(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(211,211,211,0.3)'
            )
            
            st.plotly_chart(fig_activity, use_container_width=True)
    

    st.subheader("Распределение прибыли по городам")
    
    # Загружаем данные по континентам
    africa_df = pd.read_csv("Africa_margin.csv")
    asia_df = pd.read_csv("Asia_margin.csv")
    europe_df = pd.read_csv("Europe_margin.csv")
    north_america_df = pd.read_csv("North_America_margin.csv")
    oceania_df = pd.read_csv("Oceania_margin.csv")
    south_america_df = pd.read_csv("South_America_margin.csv")
    
    # Убираем строки с null в названии города
    # south_america_df = south_america_df[south_america_df['city'].notna()]
    
    # Добавляем колонку с континентом
    africa_df['continent'] = 'Africa'
    asia_df['continent'] = 'Asia'
    europe_df['continent'] = 'Europe'
    north_america_df['continent'] = 'North America'
    oceania_df['continent'] = 'Oceania'
    south_america_df['continent'] = 'South America'
    
    # Объединяем все данные
    all_cities_df = pd.concat([
        africa_df, asia_df, europe_df, 
        north_america_df, oceania_df, south_america_df
    ], ignore_index=True)
    
    # Выбор режима отображения
    map_mode = st.radio(
        "Выберите режим отображения:",
        options=["Весь мир", "По континентам"],
        horizontal=True,
        key="map_mode"
    )
    
    if map_mode == "Весь мир":
        st.subheader("Мировая карта прибыли")
        
        # Создаем мировую карту
        fig_world = go.Figure()
        
        # Добавляем точки для всех городов
        fig_world.add_trace(go.Scattergeo(
            lon=all_cities_df['lon'],
            lat=all_cities_df['lat'],
            text=all_cities_df['city'] + '<br>Прибыль: ' + all_cities_df['total_margin'].round(0).astype(int).astype(str) + ' ₽<br>Заказов: ' + all_cities_df['orders_count'].astype(str),
            mode='markers',
            marker=dict(
                size=all_cities_df['total_margin'] / all_cities_df['total_margin'].max() * 30 + 5,
                color=all_cities_df['total_margin'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(
                    title="Прибыль (₽)",
                    tickformat=",.0f"
                ),
                line=dict(width=0.5, color='white')
            ),
            hovertemplate='<b>%{text}</b><extra></extra>'
        ))
        
        fig_world.update_layout(
            title=dict(
                text="Распределение прибыли по городам мира",
                font=dict(size=20)
            ),
            geo=dict(
                projection_type='natural earth',
                showland=True,
                landcolor='rgb(243, 243, 243)',
                coastlinecolor='rgb(204, 204, 204)',
                showocean=True,
                oceancolor='rgb(230, 245, 255)',
                showcountries=True,
                countrycolor='rgb(204, 204, 204)',
                countrywidth=0.5,
                showframe=False
            ),
            height=600,
            margin=dict(l=10, r=10, t=50, b=10)
        )
        
        st.plotly_chart(fig_world, use_container_width=True)
        
        # Статистика по миру
        st.subheader("Мировая статистика")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Всего городов",
                len(all_cities_df)
            )
        
        with col2:
            total_margin = all_cities_df['total_margin'].sum()
            st.metric(
                "Общая прибыль",
                f"{total_margin:,.0f} ₽".replace(",", " ")
            )
        
        with col3:
            total_orders = all_cities_df['orders_count'].sum()
            st.metric(
                "Всего заказов",
                f"{total_orders:,}".replace(",", " ")
            )
        
        with col4:
            avg_margin = all_cities_df['total_margin'].mean()
            st.metric(
                "Средняя прибыль",
                f"{avg_margin:,.0f} ₽".replace(",", " ")
            )

        with col5:
            top10_margin = all_cities_df.nlargest(10, 'total_margin')['total_margin'].sum()
            top10_share = (top10_margin / total_margin) * 100
            st.metric(
                "Доля топ-10 городов",
                f"{top10_share:.1f}%"
            )    
        
    
    else:  # По континентам
        # Выбор континента
        continent = st.selectbox(
            "Выберите континент:",
            options=['Africa', 'Asia', 'Europe', 'North America', 'Oceania', 'South America'],
            format_func=lambda x: {
                'Africa': 'Африка',
                'Asia': 'Азия',
                'Europe': 'Европа',
                'North America': 'Северная Америка',
                'Oceania': 'Австралия',
                'South America': 'Южная Америка'
            }[x],
            key="continent_select"
        )
        
        # Выбираем данные для континента
        continent_df = all_cities_df[all_cities_df['continent'] == continent]
        
        # Определяем центр карты для каждого континента
        continent_centers = {
            'Africa': dict(lat=0, lon=20),
            'Asia': dict(lat=35, lon=100),
            'Europe': dict(lat=50, lon=10),
            'North America': dict(lat=40, lon=-100),
            'Oceania': dict(lat=-25, lon=135),
            'South America': dict(lat=-15, lon=-60)
        }
        
        # Создаем карту континента
        fig_continent = go.Figure()
        
        fig_continent.add_trace(go.Scattergeo(
            lon=continent_df['lon'],
            lat=continent_df['lat'],
            text=continent_df['city'] + '<br>Прибыль: ' + continent_df['total_margin'].round(0).astype(int).astype(str) + ' ₽<br>Заказов: ' + continent_df['orders_count'].astype(str),
            mode='markers',
            marker=dict(
                size=continent_df['total_margin'] / continent_df['total_margin'].max() * 40 + 8,
                color=continent_df['total_margin'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(
                    title="Прибыль (₽)",
                    tickformat=",.0f"
                ),
                line=dict(width=1, color='white')
            ),
            hovertemplate='<b>%{text}</b><extra></extra>'
        ))
        
        continent_names = {
            'Africa': 'Африка',
            'Asia': 'Азия',
            'Europe': 'Европа',
            'North America': 'Северная Америка',
            'Oceania': 'Австралия',
            'South America': 'Южная Америка'
        }
        
        fig_continent.update_layout(
            title=dict(
                text=f"Распределение прибыли по городам - {continent_names[continent]}",
                font=dict(size=20)
            ),
            geo=dict(
                projection_type='natural earth',
                center=continent_centers[continent],
                projection_scale=1.5 if continent in ['Europe', 'Oceania'] else 1,
                showland=True,
                landcolor='rgb(243, 243, 243)',
                coastlinecolor='rgb(204, 204, 204)',
                showocean=True,
                oceancolor='rgb(230, 245, 255)',
                showcountries=True,
                countrycolor='rgb(204, 204, 204)',
                countrywidth=0.5,
                showframe=False
            ),
            height=600,
            margin=dict(l=10, r=10, t=50, b=10)
        )
        
        st.plotly_chart(fig_continent, use_container_width=True)
        
        # Статистика по континенту
        st.subheader(f"Статистика - {continent_names[continent]}")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Всего городов",
                len(continent_df)
            )
        
        with col2:
            total_margin = continent_df['total_margin'].sum()
            st.metric(
                "Общая прибыль",
                f"{total_margin:,.0f} ₽".replace(",", " ")
            )
        
        with col3:
            total_orders = continent_df['orders_count'].sum()
            st.metric(
                "Всего заказов",
                f"{total_orders:,}".replace(",", " ")
            )
        
        with col4:
            avg_margin = continent_df['total_margin'].mean()
            st.metric(
                "Средняя прибыль",
                f"{avg_margin:,.0f} ₽".replace(",", " ")
            )
        
        # # Топ-10 городов континента
        # st.subheader(f"Топ-10 городов - {continent_names[continent]}")
        
        # top_continent = continent_df.nlargest(10, 'total_margin')[
        #     ['city', 'total_margin', 'orders_count']
        # ]
        
        # st.dataframe(
        #     top_continent,
        #     use_container_width=True,
        #     hide_index=True,
        #     column_config={
        #         "city": "Город",
        #         "total_margin": st.column_config.NumberColumn(
        #             "Прибыль",
        #             format="%,.0f ₽"
        #         ),
        #         "orders_count": st.column_config.NumberColumn(
        #             "Заказов",
        #             format="%d"
        #         )
        #     }
        # )

    st.subheader("Распределение прибыли по континентам")

    # Загружаем данные
    continent_df = pd.read_csv("continent_margin_summary.csv")

    # Создаем две колонки
    col_pie, col_info = st.columns([1.5, 1])

    with col_pie:
        # Цвета для континентов
        continent_colors = {
            'Asia': '#1f77b4',
            'North_America': '#ff7f0e', 
            'Europe': '#2ca02c',
            'South_America': '#d62728',
            'Oceania':"#7ce472",
            'Africa': '#8c564b'
        }
        
        # Создаем список цветов в порядке континентов
        colors_list = [continent_colors[cont] for cont in continent_df['continent']]
        
        # Создаем pie chart через Plotly
        fig_pie = go.Figure(data=[go.Pie(
            labels=continent_df['continent'].map({
                'Asia': 'Азия',
                'North_America': 'Северная Америка',
                'Europe': 'Европа',
                'South_America': 'Южная Америка',
                'Oceania': 'Австралия',
                'Africa': 'Африка'
            }),
            values=continent_df['total_margin'],
            textinfo='percent',
            textposition='inside',
            hole=0.0,
            marker=dict(
                colors=colors_list,
                line=dict(color='white', width=1.5)
            ),
            hovertemplate='<b>%{label}</b><br>Прибыль: %{value:,.0f} ₽<br>Доля: %{percent}<extra></extra>',
            sort=False
        )])
        
        fig_pie.update_layout(
            # title="Распределение абсолютной прибыли по континентам",
            height=400,
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(size=12),
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_info:
        st.write("**Континенты**")
        
        # Сортируем по убыванию маржи
        display_df = continent_df.sort_values('total_margin', ascending=False).copy()
        
        # Рассчитываем проценты
        total = display_df['total_margin'].sum()
        display_df['percentage'] = (display_df['total_margin'] / total * 100).round(1)
        
        # Цвета для континентов
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#8c564b']
        
        # Названия континентов на русском
        continent_names = {
            'Asia': 'Азия',
            'North_America': 'Северная Америка',
            'Europe': 'Европа',
            'South_America': 'Южная Америка',
            'Oceania': 'Австралия',
            'Africa': 'Африка'
        }
        
        # Выводим каждый континент отдельной строкой
        for i, (_, row) in enumerate(display_df.iterrows()):
            color = colors[i % len(colors)]
            margin_formatted = f"{row['total_margin']:,.0f}".replace(",", " ")
            
            st.markdown(
                f"<div style='display: flex; align-items: center; margin-bottom: 15px;'>"
                f"<div style='width: 12px; height: 12px; background-color: {color}; "
                f"border-radius: 3px; margin-right: 10px;'></div>"
                f"<div style='flex: 1;'>"
                f"<div style='font-weight: bold;'>{continent_names[row['continent']]}</div>"
                f"<div style='font-size: 12px; color: #666;'>{margin_formatted} ₽</div>"
                f"<div style='font-size: 12px; color: #999;'>{row['cities_covered']} городов, {row['orders_count']:,} заказов</div>"
                f"</div>"
                f"<div style='font-size: 18px; font-weight: bold;'>{row['percentage']:.1f}%</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        
        # Итого
        total_formatted = f"{total:,.0f}".replace(",", " ")
        total_cities = display_df['cities_covered'].sum()
        total_orders = display_df['orders_count'].sum()
        
        st.divider()
        st.markdown(
            f"<div style='display: flex; justify-content: space-between;'>"
            f"<span style='font-weight: bold;'>Итого</span>"
            f"<span style='font-weight: bold;'>{total_formatted} ₽</span>"
            f"</div>",
            unsafe_allow_html=True
        )
        st.caption(f"Всего городов: {total_cities}, всего заказов: {total_orders:,}".replace(",", " "))

    # --- ТОП-30 ГОРОДОВ ПО СУММАРНОЙ МАРЖЕ ---
    st.subheader("Топ-30 городов по суммарной прибыли")

    # Загружаем данные
    city_margin_df = pd.read_csv("city_margin_distribution.csv")

    # Берем топ-30 городов
    top_30_cities = city_margin_df.nlargest(30, 'total_margin')

    # Сортируем по убыванию для отображения (слева направо от большего к меньшему)
    top_30_cities = top_30_cities.sort_values('total_margin', ascending=False)

    # Создаем вертикальный bar chart
    fig_top_cities = go.Figure()

    fig_top_cities.add_trace(go.Bar(
        x=top_30_cities['city'],
        y=top_30_cities['total_margin'],
        marker=dict(
            color=top_30_cities['total_margin'],
            colorscale='Plasma',  # от фиолетового через красный к желтому
            showscale=True,
            colorbar=dict(
                title="Прибыль (₽)",
                tickformat=",.0f"
            ),
            line=dict(width=0)
        ),
        text=top_30_cities['total_margin'].apply(lambda x: f'{x:,.0f} ₽'.replace(',', ' ')),
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Прибыль: %{y:,.0f} ₽<br>Доля от общей: %{customdata:.2f}%<extra></extra>',
        customdata=top_30_cities['margin_share'] * 100
    ))

    fig_top_cities.update_layout(
        # title="Топ-30 городов по суммарной прибыли",
        xaxis_title="",
        yaxis_title="Суммарная прибыль (₽)",
        height=500,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
        margin=dict(l=20, r=20, t=40, b=80),
        showlegend=False
    )

    fig_top_cities.update_xaxes(
        showgrid=False,
        tickangle=45,
        tickfont=dict(size=10)
    )

    fig_top_cities.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(211,211,211,0.3)',
        tickformat=',.0f'
    )

    st.plotly_chart(fig_top_cities, use_container_width=True)

    # Дополнительная информация
    col1, col2, col3 = st.columns(3)

    with col1:
        total_top30_margin = top_30_cities['total_margin'].sum()
        st.metric(
            "Суммарная прибыль топ-30",
            f"{total_top30_margin:,.0f} ₽".replace(',', ' ')
        )

    with col2:
        total_top30_share = top_30_cities['margin_share'].sum() * 100
        st.metric(
            "Доля от общей прибыли",
            f"{total_top30_share:.1f}%"
        )

    with col3:
        avg_top30_margin = top_30_cities['total_margin'].mean()
        st.metric(
            "Средняя прибыль в топ-30",
            f"{avg_top30_margin:,.0f} ₽".replace(',', ' ')
        )   

    # --- СРАВНЕНИЕ ИНТЕНСИВНОСТИ ВОЗВРАТОВ ПО МАКРО-РЕГИОНАМ ---
    st.subheader("Сравнение интенсивности возвратов по макро-регионам")

    # Загружаем данные
    return_rates_df = pd.read_csv("continent_return_rates.csv")

    # Сортируем по убыванию return rate
    return_rates_df = return_rates_df.sort_values('avg_return_rate', ascending=False)

    # Названия континентов на русском
    continent_names = {
        'Africa': 'Африка',
        'Europe': 'Европа',
        'South_America': 'Южная Америка',
        'Asia_Japan_Australia': 'Азия, Япония, Австралия',
        'North_America': 'Северная Америка'
    }

    # Создаем столбец с русскими названиями
    return_rates_df['continent_ru'] = return_rates_df['continent'].map(continent_names)

    # Создаем вертикальный bar chart
    fig_returns = go.Figure()

    fig_returns.add_trace(go.Bar(
        x=return_rates_df['continent_ru'],
        y=return_rates_df['avg_return_rate'],
        marker=dict(
            color=return_rates_df['avg_return_rate'],
            colorscale='Reds',
            showscale=True,
            colorbar=dict(
                title="Доля возвратов",
                tickformat='.1%'
            ),
            line=dict(width=0)
        ),
        text=return_rates_df['avg_return_rate'].apply(lambda x: f'{x:.2%}'),
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Доля возвратов: %{y:.2%}<br>Возвратов: %{customdata[0]:,}<br>Заказов: %{customdata[1]:,}<extra></extra>',
        customdata=return_rates_df[['total_returns', 'total_orders']].values
    ))

    fig_returns.update_layout(
        # title="Сравнение интенсивности возвратов по макро-регионам",
        xaxis_title="",
        yaxis_title="Доля возвратов",
        height=450,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
        margin=dict(l=20, r=20, t=40, b=60),
        showlegend=False
    )

    fig_returns.update_xaxes(
        showgrid=False,
        tickangle=0,
        tickfont=dict(size=11)
    )

    fig_returns.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(211,211,211,0.3)',
        tickformat='.1%'
    )

    st.plotly_chart(fig_returns, use_container_width=True)

    # Дополнительная информация
    # col1, col2 = st.columns(2)

    # with col1:
    #     st.write("**Статистика по континентам:**")
    #     display_df = return_rates_df[['continent_ru', 'total_returns', 'total_orders', 'avg_return_rate']].copy()
    #     display_df['avg_return_rate'] = display_df['avg_return_rate'] * 100
        
    #     st.dataframe(
    #         display_df,
    #         use_container_width=True,
    #         hide_index=True,
    #         column_config={
    #             "continent_ru": "Континент",
    #             "total_returns": st.column_config.NumberColumn("Возвратов", format="%d"),
    #             "total_orders": st.column_config.NumberColumn("Заказов", format="%d"),
    #             "avg_return_rate": st.column_config.NumberColumn("Доля возвратов", format="%.2f%%")
    #         }
    #     )

    # with col2:
    #     st.write("**Ключевые выводы:**")
        
    #     max_rate = return_rates_df.loc[return_rates_df['avg_return_rate'].idxmax()]
    #     min_rate = return_rates_df.loc[return_rates_df['avg_return_rate'].idxmin()]
    #     avg_rate = return_rates_df['avg_return_rate'].mean()
        
    #     st.metric(
    #         "Максимальная доля возвратов",
    #         f"{max_rate['avg_return_rate']:.2%}",
    #         f"{continent_names[max_rate['continent']]}"
    #     )
        
    #     st.metric(
    #         "Минимальная доля возвратов",
    #         f"{min_rate['avg_return_rate']:.2%}",
    #         f"{continent_names[min_rate['continent']]}"
    #     )
        
    #     st.metric(
    #         "Средняя доля возвратов",
    #         f"{avg_rate:.2%}"
    #     )
        
    #     st.caption("💡 Африка имеет самую высокую долю возвратов, Северная Америка — самую низкую")    

# --- ЭКРАН РЕКОМЕНДАЦИИ ---
elif page == "Рекомендации":
    st.header("Рекомендации")
    # st.subheader("Топ-10 категорий по вероятности покупки")
    
    # # Получаем все уникальные категории и назначаем им цвета
    # all_categories = recommendations_df['category'].unique()
    
    # # Цветовая палитра
    # colors_palette = [
    #     "#2380c2", '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    #     '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    #     '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
    #     '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5',
    #     '#393b79', '#637939', '#8c6d31', '#843c39', '#7b4173'
    # ]
    
    # # Создаем словарь цветов для категорий
    # category_colors = {}
    # for i, category in enumerate(sorted(all_categories)):
    #     category_colors[category] = colors_palette[i % len(colors_palette)]
    
    # # Функция для создания вертикального bar chart с цветами по категориям
    # def create_colored_bar_chart(df, gender, is_loyal, title, max_y=None):
    #     # Фильтруем данные
    #     segment_df = df[(df['gender'] == gender) & (df['is_loyal'] == is_loyal)].copy()
        
    #     # Берем топ-10 по вероятности
    #     segment_df = segment_df.nlargest(10, 'prob')
        
    #     # Сортируем по убыванию вероятности
    #     segment_df = segment_df.sort_values('prob', ascending=False)
        
    #     # Получаем цвета для категорий в порядке отображения
    #     bar_colors = [category_colors[cat] for cat in segment_df['category']]
        
    #     fig = go.Figure()
        
    #     fig.add_trace(go.Bar(
    #         x=segment_df['category'],
    #         y=segment_df['prob'],
    #         marker_color=bar_colors,
    #         text=segment_df['prob'].apply(lambda x: f'{x:.1%}'),
    #         textposition='outside',
    #         hovertemplate='<b>%{x}</b><br>Вероятность: %{y:.1%}<extra></extra>'
    #     ))
        
    #     # Определяем максимальное значение для оси Y
    #     if max_y is None:
    #         y_max = segment_df['prob'].max() * 1.15
    #     else:
    #         y_max = max_y
        
    #     fig.update_layout(
    #         title=title,
    #         xaxis_title="",
    #         yaxis_title="Доля категории в покупках",
    #         height=400,
    #         showlegend=False,
    #         plot_bgcolor='white',
    #         paper_bgcolor='white',
    #         margin=dict(l=20, r=20, t=40, b=80)
    #     )
        
    #     fig.update_xaxes(
    #         showgrid=False,
    #         tickangle=45,
    #         tickfont=dict(size=10)
    #     )
        
    #     fig.update_yaxes(
    #         showgrid=True,
    #         gridwidth=1,
    #         gridcolor='rgba(211,211,211,0.3)',
    #         tickformat='.0%',
    #         range=[0, y_max]
    #     )
        
    #     return fig, segment_df['prob'].max()
    
    
    
    # women_loyal_df = recommendations_df[(recommendations_df['gender'] == 'F') & (recommendations_df['is_loyal'] == True)]
    # men_loyal_df = recommendations_df[(recommendations_df['gender'] == 'M') & (recommendations_df['is_loyal'] == True)]
    
    # women_max_loyal = women_loyal_df.nlargest(10, 'prob')['prob'].max() if not women_loyal_df.empty else 0
    # men_max_loyal = men_loyal_df.nlargest(10, 'prob')['prob'].max() if not men_loyal_df.empty else 0
    # global_max = max(women_max_loyal, men_max_loyal) * 1.15
    
    # col_f1, col_f2 = st.columns(2)
    
    # with col_f1:
    #     if not women_loyal_df.empty:
    #         fig_f_true, _ = create_colored_bar_chart(
    #             recommendations_df, gender='F', is_loyal=True, 
    #             title="Женщины", max_y=global_max
    #         )
    #         st.plotly_chart(fig_f_true, use_container_width=True)
    #     else:
    #         st.info("Нет данных для лояльных женщин")
    
    # with col_f2:
    #     if not men_loyal_df.empty:
    #         fig_m_true, _ = create_colored_bar_chart(
    #             recommendations_df, gender='M', is_loyal=True,
    #             title="Мужчины", max_y=global_max
    #         )
    #         st.plotly_chart(fig_m_true, use_container_width=True)
    #     else:
    #         st.info("Нет данных для лояльных мужчин")
   

    st.subheader("🎯 Вероятность покупки по категориям")

    # Загрузка данных
    @st.cache_data
    def load_share_data():
        male_share = pd.read_csv("male_orders_share.csv")
        female_share = pd.read_csv("female_orders_share.csv")
        return male_share, female_share

    male_share, female_share = load_share_data()

    # Преобразуем share в проценты
    male_share["share_percent"] = male_share["share"] * 100
    female_share["share_percent"] = female_share["share"] * 100

    # Сортируем по убыванию доли
    male_sorted = male_share.sort_values("share", ascending=False).copy()
    female_sorted = female_share.sort_values("share", ascending=False).copy()

    # Создаём два графика рядом
    col_hist1, col_hist2 = st.columns(2)

    with col_hist1:
        # st.markdown("**Женщины**")
        
        # Создаём словарь с уникальными цветами для каждой категории
        categories_female = female_sorted["category"].tolist()
        # Используем качественную палитру с большим количеством цветов
        color_palette = px.colors.qualitative.Plotly + px.colors.qualitative.Set3 + px.colors.qualitative.Pastel
        female_colors = {cat: color_palette[i % len(color_palette)] for i, cat in enumerate(categories_female)}
        
        fig_female = px.bar(
            female_sorted,
            x="category",
            y="share_percent",
            color="category",
            color_discrete_map=female_colors,  # используем словарь с цветами
            labels={"share_percent": "Вероятность покупки (%)", "category": ""},
            text="share_percent",
            title="Женщины"
        )
        
        fig_female.update_traces(
            texttemplate='%{text:.1f}%',
            textposition='outside',
            textfont=dict(size=10)
        )
        
        fig_female.update_layout(
            yaxis_title="Доля категории в покупках",
            yaxis=dict(range=[0, female_sorted["share_percent"].max() * 1.15]),
            height=500,
            showlegend=False,  # включаем легенду, чтобы видеть соответствие цветов
            # legend_title="Категория",
            xaxis_tickangle=-45
        )
        
        st.plotly_chart(fig_female, use_container_width=True)

    with col_hist2:
        # st.markdown("**Мужчины**")
        
        # То же самое для мужчин
        categories_male = male_sorted["category"].tolist()
        male_colors = {cat: color_palette[i % len(color_palette)] for i, cat in enumerate(categories_male)}
        
        fig_male = px.bar(
            male_sorted,
            x="category",
            y="share_percent",
            color="category",
            color_discrete_map=male_colors,
            labels={"share_percent": "Вероятность покупки (%)", "category": ""},
            text="share_percent",
            title="Мужчины"
        )
        
        fig_male.update_traces(
            texttemplate='%{text:.1f}%',
            textposition='outside',
            textfont=dict(size=10)
        )
        
        fig_male.update_layout(
            yaxis_title="Доля категории в покупках",
            yaxis=dict(range=[0, male_sorted["share_percent"].max() * 1.15]),
            height=500,
            showlegend=False,
            # legend_title="Категория",
            xaxis_tickangle=-45
        )
        
        st.plotly_chart(fig_male, use_container_width=True)
        
    st.divider()
    

    st.subheader("Рекомендованные бренды")
    st.caption("Выберите пол и категорию для получения рекомендаций")

    # Функция для рекомендаций (обновлённая)
    def recommend_brands_streamlit(gender: str, category: str, n: int = 20, sort_type: str = "actual", risk_level: str = "medium", path: str = "results"):
        gender_map = {'M': 'male', 'F': 'female'}
        
        if gender not in gender_map:
            st.error("Некорректный пол")
            return pd.DataFrame()
        
        valid_sorts = ['actual', 'price_desc', 'price_asc', 'popularity', 'rating']
        if sort_type not in valid_sorts:
            st.error("Некорректный тип сортировки")
            return pd.DataFrame()
        
        # Формируем имя файла с учётом уровня риска (только для actual)
        if sort_type == "actual":
            if risk_level == "low":
                risk_suffix = "_low_risk"
            elif risk_level == "high":
                risk_suffix = "_high_risk"
            else:  # medium
                risk_suffix = "_medium_risk"
            
            filename = f"{gender_map[gender]}_{sort_type}{risk_suffix}.csv"
        else:
            filename = f"{gender_map[gender]}_{sort_type}.csv"
        
        filepath = os.path.join(path, filename)
        
        if not os.path.exists(filepath):
            st.warning(f"Файл не найден: {filepath}")
            return pd.DataFrame()
        
        df = pd.read_csv(filepath)
        df = df[df['category'] == category]
        
        if df.empty:
            return pd.DataFrame()
        
        df = df.head(n).reset_index(drop=True)
        
        # Отбираем колонки для отображения (добавляем product_name_1, product_name_2)
        display_cols = ['brand', 'rating', 'product_1', 'price_1', 'product_name_1', 'product_2', 'price_2', 'product_name_2']
        display_cols = [c for c in display_cols if c in df.columns]
        df_display = df[display_cols].copy()
        
        # Чистка NaN
        for col in ['product_1', 'product_2', 'product_name_1', 'product_name_2']:
            if col in df_display.columns:
                df_display[col] = df_display[col].fillna('—')
        
        for col in ['price_1', 'price_2']:
            if col in df_display.columns:
                df_display[col] = df_display[col].fillna(0)
        
        return df_display

    # Фильтры
    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        selected_gender = st.selectbox(
            "Выберите пол:",
            options=['F', 'M'],
            format_func=lambda x: 'Женщины' if x == 'F' else 'Мужчины',
            key="rec_gender"
        )

    with col_f2:
        # Получаем список категорий для выбранного пола
        gender_categories = sorted(gender_df[gender_df['gender'] == selected_gender]['category'].unique())
        selected_category = st.selectbox(
            "Выберите категорию:",
            options=gender_categories,
            key="rec_category"
        )

    with col_f3:
        sort_options = {
            'actual': 'По актуальности',
            'popularity': 'По популярности',
            'rating': 'По рейтингу',
            'price_desc': 'Дорогие сначала',
            'price_asc': 'Дешевые сначала'
        }
        selected_sort = st.selectbox(
            "Сортировка:",
            options=list(sort_options.keys()),
            format_func=lambda x: sort_options[x],
            key="rec_sort"
        )

    # Выбор уровня риска (только для "по актуальности")
    risk_level = "medium"  # по умолчанию
    if selected_sort == "actual":
        col_r1, col_r2 = st.columns([1, 3])
        with col_r1:
            risk_level = st.radio(
                "Уровень риска:",
                options=['low', 'medium', 'high'],
                format_func=lambda x: {
                    'low': 'Низкий',
                    'medium': 'Средний',
                    'high': 'Высокий'
                }.get(x, x),
                horizontal=True,
                key="rec_risk"
            )

    # Количество товаров
    n_items = st.slider("Количество товаров:", min_value=5, max_value=50, value=20, step=5, key="rec_n_items")

    # Кнопка для получения рекомендаций
    if st.button("Получить рекомендации", use_container_width=True, key="rec_button"):
        result_df = recommend_brands_streamlit(
            gender=selected_gender,
            category=selected_category,
            n=n_items,
            sort_type=selected_sort,
            risk_level=risk_level,
            path="."
        )
        
        if not result_df.empty:
            st.success(f"Найдено {len(result_df)} брендов")
            
            # Переименовываем колонки
            column_names = {
                'brand': 'Бренд',
                'rating': 'Рейтинг',
                'product_1': 'ID товара 1',
                'price_1': 'Цена 1 (₽)',
                'product_name_1': 'Название товара 1',
                'product_2': 'ID товара 2',
                'price_2': 'Цена 2 (₽)',
                'product_name_2': 'Название товара 2'
            }
            
            styled_df = result_df.rename(columns={k: v for k, v in column_names.items() if k in result_df.columns})
            
            # Настраиваем форматирование колонок
            column_config = {}
            for col in styled_df.columns:
                if 'Цена' in col:
                    column_config[col] = st.column_config.NumberColumn(col, format="%.0f ₽")
                elif 'Рейтинг' in col:
                    column_config[col] = st.column_config.NumberColumn(col, format="%.2f")
            
            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True,
                column_config=column_config
            )
            
        else:
            st.warning("Нет данных для выбранных параметров")
    else:
        st.info("Нажмите кнопку, чтобы получить рекомендации")