import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import os

CLEANED_DATASETS = {
    "pdiabe": "clean_data/pdiabe_cleaned.csv",
    "phearte": "clean_data/phearte_cleaned.csv",
    "phibpe": "clean_data/phibpe_cleaned.csv",
    "pcogstate": "clean_data/pcogstate_cleaned.csv"
}

def load_cleaned_data():
    df_dict = {}
    for key, path in CLEANED_DATASETS.items():
        if os.path.exists(path):
            # Load with first column as index (row names)
            df = pd.read_csv(path, index_col=0)
            df_dict[key] = df
    return df_dict

df_dict = load_cleaned_data()

INTERVENTION_OPTIONS = {
    "Diabetes Incidence Reduction": "pdiabe",
    "Heart Disease Incidence Reduction": "phearte",
    "Hypertension Incidence Reduction": "phibpe",
    "MCI/Dementia Incidence Reduction": "pcogstate"
}

OUTCOME_OPTIONS = {
    "Population": "n_startpop",
    "Nursing Home Population": "n_nhmliv",
    "Population with Dementia": "n_cogstate1",
    "Dementia Prevalence (%)": "p_cogstate1",
    "Population with MCI": "n_cogstate2",
    "MCI Prevalence (%)": "p_cogstate2",
    "Population with Diabetes": "n_diabe",
    "Diabetes Prevalence (%)": "p_diabe",
    "Population with Heart Disease": "n_hearte",
    "Heart Disease Prevalence (%)": "p_hearte",
    "Population with Hypertension": "n_hibpe",
    "Hypertension Prevalence (%)": "p_hibpe"
}

SUBGROUP_OPTIONS = {
    "Age 55-64": "5564",
    "Age 65-74": "6574",
    "Age 75-84": "7584",
    "Age 85+": "85p",
    "All": "all",
    "Non-Hispanic black": "blk",
    "At least some college": "college",
    "Female": "f",
    "Hispanic": "his",
    "Hispanic female": "his_f",
    "GED or less than high school": "hsless",
    "Male": "m",
    "Non-Hispanic white": "wht"
}


st.set_page_config(page_title="Intervention Simulation Dashboard", layout="wide")

st.markdown("""
<style>
    section[data-testid="stSidebar"] {
        background-color: #D0D7E5; 
        box-shadow: 2px 0px 15px rgba(0,0,0,0.08);
        border-right: 1px solid #E0E0E0;
        min-width: 300px;
    }
</style>
""", unsafe_allow_html=True)

st.title("US Cost of Dementia Model")
st.sidebar.header("Filters")

selected_outcome = st.sidebar.selectbox("Outcome", list(OUTCOME_OPTIONS.keys()))
selected_subgroup = st.sidebar.selectbox("Subgroup", list(SUBGROUP_OPTIONS.keys()))
selected_interventions = st.sidebar.multiselect("Choose Intervention(s)", list(INTERVENTION_OPTIONS.keys()))
start_year, end_year = st.sidebar.slider("Year Range", min_value=2026, max_value=2050, value=(2026, 2050), step=2)

intervention_levels = {}
for item in selected_interventions:
    key = INTERVENTION_OPTIONS[item]
    if key == "pcogstate":
        intervention_levels["pcogstate_1"] = st.sidebar.slider("Dementia Prevalence Reduction", 0.5, 1.0, 0.85, 0.01)
        intervention_levels["pcogstate_2"] = st.sidebar.slider("MCI Prevalence Reduction", 0.5, 1.0, 0.90, 0.01)
    else:
        intervention_levels[key] = st.sidebar.slider(f"{item} Level", 0.5, 1.0, 0.85, 0.01)

if st.sidebar.button("Run Simulation"):

    outcome_code = OUTCOME_OPTIONS[selected_outcome]
    subgroup_code = SUBGROUP_OPTIONS[selected_subgroup]
    # The column name in the CSV is [OUTCOME]_[SUBGROUP]
    target_col = f"{outcome_code}_{subgroup_code}"

    year_range = list(range(start_year, end_year + 1, 2))
    
    results_df = pd.DataFrame({"Year": year_range})
    
    # We will calculate a "Baseline" (Level=1.0) and an "Intervention" (User Level)
    # Since we can select multiple interventions, we'll plot them separately.
    
    # Check if we have at least one valid intervention to plot
    valid_plot = False

    for display_name in selected_interventions:
        key = INTERVENTION_OPTIONS[display_name]
        df = df_dict.get(key)

        if df is None:
            st.error(f"Dataset for {key} not loaded.")
            continue
            
        if target_col not in df.columns:
            st.error(f"Column '{target_col}' not found in {key} dataset.")
            continue

        # Get Beta vector (the column for this outcome/subgroup)
        # The index of df contains the row names: _cons, 2.year_inc, ivparm1, etc.
        beta = df[target_col]

        baseline_values = []
        intervention_values = []

        for year in year_range:
            year_inc = year - 2024
            
            # Common terms
            # _cons
            b_cons = beta.get("_cons", 0)
            # N.year_inc (e.g., 2.year_inc, 4.year_inc...)
            b_year = beta.get(f"{year_inc}.year_inc", 0)
            
            base_val = 0
            inter_val = 0

            if key == "pcogstate":
                # Formula:
                # Pred = _cons + N.year_inc 
                #      + ivparm1*L1 + N.year_inc#c.ivparm1*L1 
                #      + ivparm2*L2 + N.year_inc#c.ivparm2*L2 
                #      + c.ivparm1#c.ivparm2*L1*L2 + N.year_inc#c.ivparm1#c.ivparm2*L1*L2
                
                L1 = intervention_levels["pcogstate_1"]
                L2 = intervention_levels["pcogstate_2"]
                
                # Coefficients
                b_iv1 = beta.get("ivparm1", 0)
                b_year_iv1 = beta.get(f"{year_inc}.year_inc#c.ivparm1", 0)
                
                b_iv2 = beta.get("ivparm2", 0)
                b_year_iv2 = beta.get(f"{year_inc}.year_inc#c.ivparm2", 0)
                
                b_iv1_iv2 = beta.get("c.ivparm1#c.ivparm2", 0)
                b_year_iv1_iv2 = beta.get(f"{year_inc}.year_inc#c.ivparm1#c.ivparm2", 0)

                # Baseline (L1=1.0, L2=1.0)
                base_val = (b_cons + b_year + 
                           b_iv1 * 1.0 + b_year_iv1 * 1.0 +
                           b_iv2 * 1.0 + b_year_iv2 * 1.0 +
                           b_iv1_iv2 * 1.0 * 1.0 + b_year_iv1_iv2 * 1.0 * 1.0)

                # Intervention
                inter_val = (b_cons + b_year + 
                            b_iv1 * L1 + b_year_iv1 * L1 +
                            b_iv2 * L2 + b_year_iv2 * L2 +
                            b_iv1_iv2 * L1 * L2 + b_year_iv1_iv2 * L1 * L2)

            else:
                # Standard Formula:
                # Pred = _cons + N.year_inc + ivparm1*L1 + N.year_inc#c.ivparm1*L1
                
                L1 = intervention_levels[key]
                
                b_iv1 = beta.get("ivparm1", 0)
                b_year_iv1 = beta.get(f"{year_inc}.year_inc#c.ivparm1", 0)
                
                # Baseline (L1=1.0)
                base_val = b_cons + b_year + b_iv1 * 1.0 + b_year_iv1 * 1.0
                
                # Intervention
                inter_val = b_cons + b_year + b_iv1 * L1 + b_year_iv1 * L1

            baseline_values.append(base_val)
            intervention_values.append(inter_val)

        # Add to results
        # We only add baseline once (it should be roughly the same across files if the models are consistent, 
        # but technically each model predicts its own baseline. Let's just plot the baseline for the *first* selected intervention 
        # to avoid clutter, or plot them all if they differ significantly. 
        # For simplicity, let's store "Baseline ({display_name})" and "Intervention ({display_name})"
        
        # Add to results
        results_df[f"Baseline ({display_name})"] = baseline_values
        results_df[f"Intervention ({display_name})"] = intervention_values
        
        # Calculate difference
        diff_values = [i - b for i, b in zip(intervention_values, baseline_values)]
        
        results_df[f"Baseline ({display_name})"] = baseline_values
        results_df[f"Intervention ({display_name})"] = intervention_values
        results_df[f"Change ({display_name})"] = diff_values
        
        valid_plot = True

    if not valid_plot:
        st.stop()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"Projected {selected_outcome}")
        fig = go.Figure()
        
        colors = ["#990000", "#FFCC00", "#293035", "#53616a", "#bdc4c9"]
        
        for i, display_name in enumerate(selected_interventions):
            color = colors[i % len(colors)]
            key = INTERVENTION_OPTIONS[display_name]
            
            base_col = f"Baseline ({display_name})"
            inter_col = f"Intervention ({display_name})"
            
            if key == "pcogstate":
                l1 = intervention_levels["pcogstate_1"]
                l2 = intervention_levels["pcogstate_2"]
                inter_label = f"{display_name} (L1={l1}, L2={l2})"
            else:
                level = intervention_levels[key]
                inter_label = f"{display_name} (Level={level})"

            base_name = f"<b>Baseline:</b> {display_name}"
            inter_name = f"<b>Intervention:</b> {inter_label}"

            if base_col in results_df.columns:
                y_val = results_df[base_col]
                if "%" in selected_outcome:
                    y_val = y_val * 100
                    
                fig.add_trace(go.Scatter(
                    x=results_df["Year"],
                    y=y_val,
                    mode="lines",
                    name=base_name,
                    line=dict(dash="dash", color=color, width=4),
                    opacity=0.5,
                    hovertemplate=f"{base_name}<br><b>Year:</b> %{{x}}<br><b>Value:</b> %{{y:,.2f}}<extra></extra>"
                ))
                
            if inter_col in results_df.columns:
                y_val = results_df[inter_col]
                if "%" in selected_outcome:
                    y_val = y_val * 100
                    
                fig.add_trace(go.Scatter(
                    x=results_df["Year"],
                    y=y_val,
                    mode="lines+markers",
                    name=inter_name,
                    line=dict(color=color, width=2),
                    hovertemplate=f"{inter_name}<br><b>Year:</b> %{{x}}<br><b>Value:</b> %{{y:,.2f}}<extra></extra>"
                ))

        fig.update_layout(
            height=450,
            xaxis_title="Year",
            yaxis_title=selected_outcome,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=40, b=20),
            font=dict(color="black"),
            xaxis=dict(
                title_font=dict(size=14, color="black"),
                tickfont=dict(color="black", size=12),
                showgrid=True,
                gridcolor='#D0D0D0',
                showline=False
            ),
            yaxis=dict(
                title_font=dict(size=14, color="black"),
                tickfont=dict(color="black", size=12),
                showgrid=True,
                gridcolor='#D0D0D0',
                showline=False
            )
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Change from Baseline")
        fig_diff = go.Figure()
        
        for i, display_name in enumerate(selected_interventions):
            color = colors[i % len(colors)]
            diff_col = f"Change ({display_name})"
            change_name = f"<b>Change:</b> {display_name}"
            
            if diff_col in results_df.columns:
                y_val = results_df[diff_col]
                if "%" in selected_outcome:
                    y_val = y_val * 100
                    
                fig_diff.add_trace(go.Scatter(
                    x=results_df["Year"],
                    y=y_val,
                    mode="lines+markers",
                    name=change_name,
                    line=dict(color=color, width=2),
                    hovertemplate=f"{change_name}<br><b>Year:</b> %{{x}}<br><b>Difference:</b> %{{y:,.2f}}<extra></extra>"
                ))
        
        fig_diff.update_layout(
            height=450,
            xaxis_title="Year",
            yaxis_title="Difference (Intervention - Baseline)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=40, b=20),
            font=dict(color="black"),
            xaxis=dict(
                title_font=dict(size=14, color="black"),
                tickfont=dict(color="black", size=12),
                showgrid=True,
                gridcolor='#D0D0D0',
                showline=False
            ),
            yaxis=dict(
                title_font=dict(size=14, color="black"),
                tickfont=dict(color="black", size=12),
                showgrid=True,
                gridcolor='#D0D0D0',
                showline=False
            )
        )
        
        st.plotly_chart(fig_diff, use_container_width=True)

    # st.subheader("Raw Data")
    
    # styled_df = results_df.style.set_properties(**{
    #     'color': 'black',
    #     'border': '1px solid black',  
    #     'text-align': 'center',    
    #     'vertical-align': 'middle'
    # }).set_table_styles([
    #     {'selector': 'th', 'props': [
    #         ('color', 'black'), 
    #         ('font-size', '14px'), 
    #         ('border', '1px solid black'), 
    #         ('text-align', 'center'),      
    #         ('vertical-align', 'middle'),
    #         ('background-color', '#f0f2f6') 
    #     ]}, 
    #     {'selector': 'table', 'props': [
    #         ('width', '100%'),
    #         ('border-collapse', 'collapse'),
    #         ('border', '1px solid black')
    #     ]} 
    # ]).format(lambda x: "{:.2f}".format(x) if float("{:.2f}".format(x)) != 0 else "0.00")

    # st.markdown(styled_df.to_html(), unsafe_allow_html=True)
