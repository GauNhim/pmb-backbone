import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import os
import json
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="PMB Backbone Manager",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS TÙY CHỈNH (Mô phỏng giao diện Tailwind) ---
st.markdown("""
<style>
    .main-header {font-size: 26px; font-weight: bold; color: #1E40AF; margin-bottom: 20px;}
    .sub-header {font-size: 18px; font-weight: 600; color: #374151; margin-top: 10px;}
    .card-metric {
        background-color: #F3F4F6;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #3B82F6;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stButton>button {
        border-radius: 8px;
        height: 3em;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# --- KHỞI TẠO DỮ LIỆU (MOCK DATA TỪ constants.ts) ---
def init_data():
    if 'stations' not in st.session_state:
        # Dữ liệu giả lập ban đầu
        st.session_state['stations'] = [
            {
                "id": "1", "code": "QNHW002", "name": "Móng Cái", "region": "Miền Bắc", "status": "PLANNED",
                "province": "Quảng Ninh", "buildYear": "2026", "power": 60, "racks": 12,
                "manager": "Nguyễn Văn Quyền", "branchManager": "Nguyễn Văn Linh",
                "buildingType": "Cont", "category": "Quốc tế",
                "coordinates": {"lat": 21.521187, "lng": 107.961813},
                "designData": {
                    "racks": [{"id": "r1", "name": "Rack 1 (Nguồn)", "totalU": 42}],
                    "equipments": [
                        {"id": "eq1", "rackId": "r1", "name": "Nguồn Emerson 701", "model": "Netsure 701", "type": "DC", "powerW": 200, "startU": 1, "uHeight": 5, "color": "#3B82F6"}
                    ],
                    "calcItems": [],
                    "costEstimateItems": [], # Dữ liệu dự toán
                    "roomParams": {"width": 3, "length": 5, "height": 3, "tempInside": 25, "tempOutside": 40, "equipmentHeatW": 0},
                    "batteryParams": {"dcLoadW": 0, "targetBackupTime": 8, "batteryVoltage": 48, "batteryAh": 100, "efficiency": 0.9},
                    "rectParams": {"dcLoadW": 0, "batteryAh": 0, "rectifierModuleSize": 3000}
                },
                "inventory": [
                    {"id": "inv1", "itemCode": "MPD-100", "itemName": "Máy phát điện Cummins 100kVA", "quantity": 1, "ratedPower": 40, "type": "OFFLINE", "unit": "Cái", "location1": "Sân trạm", "transfer": {"isTransferred": False}}
                ]
            },
            {
                "id": "2", "code": "NBHW001", "name": "Nam Định", "region": "Miền Bắc", "status": "ACTIVE",
                "province": "Ninh Bình", "buildYear": "2013", "power": 15, "racks": 5,
                "manager": "Nguyễn Văn Quyền", "branchManager": "Nguyễn Đình Dương",
                "buildingType": "Cont", "category": "Repeater",
                "coordinates": {"lat": 20.42027, "lng": 106.16459},
                "designData": {}, "inventory": []
            },
            # ... Thêm các trạm khác tương tự file constants.ts
             {
                "id": "3", "code": "QNIW001", "name": "Ngọc Hồi", "region": "Miền Trung", "status": "ACTIVE",
                "province": "Quảng Ngãi", "buildYear": "2014", "power": 12, "racks": 5,
                "buildingType": "Cont", "category": "Repeater",
                "coordinates": {"lat": 14.704680, "lng": 107.685551},
                "designData": {}, "inventory": []
            }
        ]
    
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = [{"role": "model", "parts": ["Xin chào! Tôi là trợ lý ảo PMB. Tôi có thể giúp gì cho bạn về dữ liệu hạ tầng?"]}]

init_data()

# --- HÀM TIỆN ÍCH ---
def get_station_by_id(station_id):
    return next((s for s in st.session_state['stations'] if s['id'] == station_id), None)

def update_station_data(station_id, key, value):
    for s in st.session_state['stations']:
        if s['id'] == station_id:
            s[key] = value
            break

# --- 1. DASHBOARD ---
def render_dashboard():
    st.markdown('<div class="main-header">Tổng quan hệ thống PMB</div>', unsafe_allow_html=True)
    stations = st.session_state['stations']
    df = pd.DataFrame(stations)

    # Metrics
    total = len(stations)
    active = len(df[df['status'] == 'ACTIVE'])
    planned = len(df[df['status'] == 'PLANNED'])
    offline = len(df[df['status'] == 'OFFLINE'])
    total_power = sum([float(s.get('power', 0)) for s in stations])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng số trạm", total, "Trạm")
    c2.metric("Đang hoạt động", active, f"{round(active/total*100 if total else 0)}%")
    c3.metric("Đang triển khai", planned, "Dự án mới")
    c4.metric("Tổng công suất", f"{total_power} kW")

    # Charts
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.subheader("Phân bố theo Khu vực")
        if not df.empty:
            fig = px.pie(df, names='region', title='Tỷ lệ trạm theo vùng', hole=0.4, color_discrete_sequence=px.colors.qualitative.Prism)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_chart2:
        st.subheader("Trạng thái trạm")
        if not df.empty:
            fig2 = px.bar(df['status'].value_counts().reset_index(), x='status', y='count', 
                          title="Số lượng trạm theo trạng thái", labels={'count': 'Số lượng', 'status': 'Trạng thái'},
                          color='status')
            st.plotly_chart(fig2, use_container_width=True)

# --- 2. DANH SÁCH TRẠM ---
def render_station_list():
    st.markdown('<div class="main-header">Danh sách trạm tuyến trục</div>', unsafe_allow_html=True)
    df = pd.DataFrame(st.session_state['stations'])
    
    # Filter
    c1, c2, c3 = st.columns([2, 1, 1])
    search = c1.text_input("Tìm kiếm (Tên, Mã trạm, Tỉnh)", placeholder="Nhập từ khóa...")
    region_filter = c2.selectbox("Khu vực", ["Tất cả"] + list(df['region'].unique()) if not df.empty else [])
    
    # Apply Filter
    if not df.empty:
        if search:
            df = df[df['name'].str.contains(search, case=False) | df['code'].str.contains(search, case=False) | df['province'].str.contains(search, case=False)]
        if region_filter != "Tất cả":
            df = df[df['region'] == region_filter]

        st.dataframe(
            df[['code', 'name', 'province', 'region', 'status', 'power', 'buildingType', 'manager']],
            column_config={
                "code": "Mã trạm", "name": "Tên trạm", "province": "Tỉnh/TP",
                "region": "Khu vực", "status": "Trạng thái", "power": st.column_config.NumberColumn("Công suất (kW)"),
                "buildingType": "Loại nhà", "manager": "Nhân sự PMB"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Chưa có dữ liệu trạm.")

# --- 3. TÍNH TOÁN THIẾT KẾ (FEATURE CHÍNH) ---
def render_design_calculations():
    st.markdown('<div class="main-header">Tính toán thiết kế & Dự toán</div>', unsafe_allow_html=True)

    # Chọn trạm
    stations = st.session_state['stations']
    station_options = {s['id']: f"{s['code']} - {s['name']}" for s in stations}
    selected_id = st.selectbox("Chọn trạm làm việc:", options=list(station_options.keys()), format_func=lambda x: station_options[x])
    
    station = get_station_by_id(selected_id)
    if not station: return

    # Init data if missing
    if 'designData' not in station:
        station['designData'] = {}
    
    design_data = station['designData']
    
    # Tabs
    tab_layout, tab_power, tab_battery, tab_cost = st.tabs(["🏗️ Bố trí Rack", "⚡ Tính Công suất", "🔋 Tính Ắc quy", "💰 Dự toán"])

    # --- TAB: BỐ TRÍ RACK (Simplified) ---
    with tab_layout:
        st.info("Chức năng bố trí Rack trực quan (Drag & Drop) được hỗ trợ tốt nhất trên phiên bản React. Dưới đây là danh sách thiết bị hiện tại.")
        equipments = design_data.get('equipments', [])
        if equipments:
            st.dataframe(pd.DataFrame(equipments)[['name', 'model', 'type', 'powerW', 'rackId', 'startU']])
        else:
            st.warning("Chưa có thiết bị trong Rack.")

    # --- TAB: TÍNH CÔNG SUẤT ---
    with tab_power:
        st.subheader("Bảng tính toán công suất trạm")
        
        calc_items = design_data.get('calcItems', [])
        
        # Tạo cấu trúc DataFrame mặc định
        df_schema = {
            "name": "Thiết bị A", "model": "", "quantity": 1, 
            "powerRatedW": 0.0, "voltage": 48.0, "current": 0.0,
            "wireSection": "", "wireType": "1 pha 2 dây: 2x... mm2", "note": "", "type": "DC"
        }
        
        if not calc_items:
            df_calc = pd.DataFrame([df_schema])
        else:
            df_calc = pd.DataFrame(calc_items)

        # Editor
        edited_power_df = st.data_editor(
            df_calc,
            num_rows="dynamic",
            column_config={
                "name": st.column_config.TextColumn("Tên thiết bị", width="medium"),
                "quantity": st.column_config.NumberColumn("SL", min_value=0, step=1),
                "powerRatedW": st.column_config.NumberColumn("P danh định (W)", min_value=0),
                "voltage": st.column_config.NumberColumn("U (V)", min_value=0),
                "current": st.column_config.NumberColumn("I (A)", disabled=True), # Auto calc
                "wireSection": "Tiết diện dây (mm2)",
                "wireType": st.column_config.SelectboxColumn("Loại dây", options=[
                    "1 pha 2 dây: 2x... mm2 - Cu/PVC",
                    "1 pha 1 dây 1 x ... mm2 - Cu/PVC",
                    "3 pha 3 dây: 3x ... mm2- Cu/PVC/PVC",
                    "3 pha 4 dây 3x... + 1x... mm2 -Cu/PVC/PVC"
                ], width="large"),
                "type": st.column_config.SelectboxColumn("Loại", options=["DC", "AC", "PASSIVE"]),
                "note": "Ghi chú"
            },
            key=f"power_editor_{selected_id}"
        )

        # Logic tính toán tự động & Lưu
        if not edited_power_df.empty:
            # Calculate Current I = P / U
            edited_power_df['current'] = edited_power_df.apply(
                lambda x: round(x['powerRatedW'] / x['voltage'], 2) if x['voltage'] > 0 else 0, axis=1
            )
            
            # Tính tổng
            total_load = (edited_power_df['quantity'] * edited_power_df['powerRatedW']).sum()
            
            st.success(f"⚡ TỔNG CÔNG SUẤT TRẠM: **{total_load:,.0f} W**")
            
            if st.button("Lưu bảng công suất"):
                design_data['calcItems'] = edited_power_df.to_dict('records')
                st.toast("Đã lưu dữ liệu công suất!")

    # --- TAB: TÍNH ẮC QUY ---
    with tab_battery:
        st.subheader("Tính toán thời gian dự phòng Ắc quy")
        batt_params = design_data.get('batteryParams', {"dcLoadW": 0, "targetBackupTime": 4, "batteryAh": 100})
        
        c1, c2 = st.columns(2)
        with c1:
            dc_load = st.number_input("Tải DC (W)", value=float(batt_params.get('dcLoadW', 0)))
            backup_time = st.number_input("Thời gian backup mong muốn (h)", value=float(batt_params.get('targetBackupTime', 4)))
        with c2:
            batt_ah = st.selectbox("Dung lượng 1 tổ (Ah)", [50, 100, 150, 200], index=1)
            voltage = st.number_input("Điện áp hệ thống (V)", value=48, disabled=True)
            eff = 0.9 # Hiệu suất

        if st.button("Tính toán & Lưu cấu hình Ắc quy"):
            # Công thức: Ah = (P * t) / (V * eff)
            ah_req = (dc_load * backup_time) / (voltage * eff)
            n_strings = ah_req / batt_ah
            
            design_data['batteryParams'] = {"dcLoadW": dc_load, "targetBackupTime": backup_time, "batteryAh": batt_ah}
            
            st.info(f"""
            **Kết quả tính toán:**
            - Dung lượng yêu cầu: `{ah_req:.2f} Ah`
            - Số tổ ắc quy ({batt_ah}Ah) cần thiết: `{n_strings:.2f}` tổ
            - **Khuyến nghị:** Trang bị **{int(n_strings) + 1}** tổ.
            """)

    # --- TAB: DỰ TOÁN (Yêu cầu mới) ---
    with tab_cost:
        st.subheader("Dự toán thiết bị & Vật tư")
        
        # 1. Sync Logic (Đồng bộ từ Layout/Power sang Dự toán)
        if st.button("🔄 Đồng bộ từ Bảng Công suất / Rack"):
            existing_cost = design_data.get('costEstimateItems', [])
            
            # Giả lập lấy từ Calc Items để đưa vào dự toán
            calc_items = design_data.get('calcItems', [])
            new_items = []
            for item in calc_items:
                # Kiểm tra trùng lặp đơn giản
                if not any(c['itemName'] == item['name'] for c in existing_cost):
                    new_items.append({
                        "category": "MAIN", # Vật tư chính
                        "itemCode": "",
                        "itemName": item['name'],
                        "unit": "Cái",
                        "quantity": item['quantity'],
                        "unitPrice": 0,
                        "condition": "Mới",
                        "note": "Đồng bộ từ bảng CS"
                    })
            
            design_data['costEstimateItems'] = existing_cost + new_items
            st.success(f"Đã đồng bộ thêm {len(new_items)} mục vào dự toán.")

        # 2. Table Editor
        cost_items = design_data.get('costEstimateItems', [])
        cost_schema = {
            "category": "AUX", "itemCode": "", "itemName": "", "unit": "Cái",
            "quantity": 1, "unitPrice": 0, "condition": "Mới", "note": ""
        }
        
        if not cost_items:
            df_cost = pd.DataFrame([cost_schema])
        else:
            df_cost = pd.DataFrame(cost_items)

        st.caption("Phân loại: MAIN (Vật tư chính), AUX (Vật tư phụ). Nhập giá để tính thành tiền.")
        
        edited_cost_df = st.data_editor(
            df_cost,
            num_rows="dynamic",
            column_config={
                "category": st.column_config.SelectboxColumn("Phân loại", options=["MAIN", "AUX"], required=True),
                "itemCode": "Mã VT",
                "itemName": st.column_config.TextColumn("Tên vật tư", width="large"),
                "unit": st.column_config.TextColumn("Đơn vị", width="small"),
                "quantity": st.column_config.NumberColumn("SL", min_value=1),
                "unitPrice": st.column_config.NumberColumn("Đơn giá (VNĐ)", format="%d đ"),
                "condition": st.column_config.SelectboxColumn("Tình trạng", options=["Mới", "Sử dụng lại"]),
                "note": "Ghi chú"
            },
            key=f"cost_editor_{selected_id}"
        )

        if not edited_cost_df.empty:
            # Tính thành tiền
            edited_cost_df['totalAmount'] = edited_cost_df['quantity'] * edited_cost_df['unitPrice']
            grand_total = edited_cost_df['totalAmount'].sum()
            
            st.markdown(f"### 💰 TỔNG GIÁ TRỊ DỰ TOÁN: :red[{grand_total:,.0f} VNĐ]")

            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("Lưu bảng Dự toán"):
                    # Lưu lại, bỏ cột thành tiền (vì là tính toán)
                    save_df = edited_cost_df.drop(columns=['totalAmount'], errors='ignore')
                    design_data['costEstimateItems'] = save_df.to_dict('records')
                    st.toast("Đã lưu dự toán!")
            
            with col_btn2:
                if st.button("➡️ Đồng bộ sang 'Vật tư thiết bị'"):
                    # Logic chuyển sang Inventory tab
                    current_inventory = station.get('inventory', [])
                    count_added = 0
                    for _, row in edited_cost_df.iterrows():
                        # Tạo Inventory Item từ Cost Item
                        new_inv = {
                            "id": f"sync_{datetime.now().timestamp()}_{row['itemName']}",
                            "itemCode": row['itemCode'],
                            "itemName": row['itemName'],
                            "quantity": row['quantity'],
                            "unit": row['unit'],
                            "type": "OFFLINE",
                            "status": "PLANNED",
                            "note": f"Đồng bộ từ Dự toán. {row['note']}",
                            "transfer": {"isTransferred": False}
                        }
                        current_inventory.append(new_inv)
                        count_added += 1
                    
                    station['inventory'] = current_inventory
                    st.success(f"Đã chuyển {count_added} thiết bị sang danh sách Quản lý vật tư!")

# --- 4. TRỢ LÝ AI (GEMINI) ---
def render_ai_assistant():
    st.markdown('<div class="main-header">Trợ lý ảo AI (Gemini)</div>', unsafe_allow_html=True)
    
    api_key = os.getenv("API_KEY")
    if not api_key:
        api_key = st.text_input("Nhập Google API Key để kích hoạt AI:", type="password")
    
    if api_key:
        genai.configure(api_key=api_key)
        
        # Display chat history
        for msg in st.session_state['chat_history']:
            with st.chat_message(msg['role']):
                st.markdown(msg['parts'][0])
        
        if prompt := st.chat_input("Hỏi về trạm, quy chuẩn, hoặc phân tích dữ liệu..."):
            st.chat_message("user").markdown(prompt)
            st.session_state['chat_history'].append({"role": "user", "parts": [prompt]})
            
            # Prepare context
            stations_json = json.dumps(st.session_state['stations'], default=lambda o: '<not serializable>')
            context = f"Bạn là trợ lý PMB. Dữ liệu các trạm hiện tại: {stations_json}. Hãy trả lời ngắn gọn."
            
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content([context, prompt])
                st.chat_message("model").markdown(response.text)
                st.session_state['chat_history'].append({"role": "model", "parts": [response.text]})
            except Exception as e:
                st.error(f"Lỗi AI: {e}")

# --- 5. VẬT TƯ THIẾT BỊ ---
def render_inventory():
    st.markdown('<div class="main-header">Quản lý Vật tư thiết bị</div>', unsafe_allow_html=True)
    
    stations = st.session_state['stations']
    station_names = {s['id']: s['name'] for s in stations}
    s_id = st.selectbox("Chọn trạm:", list(station_names.keys()), format_func=lambda x: station_names[x], key="inv_select")
    
    station = get_station_by_id(s_id)
    inventory = station.get('inventory', [])
    
    if inventory:
        st.dataframe(pd.DataFrame(inventory))
    else:
        st.info("Trạm này chưa có dữ liệu vật tư.")

# --- NAVIGATION ---
with st.sidebar:
    st.title("PMB Manager")
    menu = st.radio("Menu", ["Tổng quan", "Danh sách trạm", "Vật tư thiết bị", "Tính toán thiết kế", "Trợ lý AI"])
    st.divider()
    st.caption("Phiên bản Python v1.0")

if menu == "Tổng quan":
    render_dashboard()
elif menu == "Danh sách trạm":
    render_station_list()
elif menu == "Tính toán thiết kế":
    render_design_calculations()
elif menu == "Vật tư thiết bị":
    render_inventory()
elif menu == "Trợ lý AI":
    render_ai_assistant()
