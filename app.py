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

# --- CSS TÙY CHỈNH ---
st.markdown("""
<style>
    .main-header {font-size: 24px; font-weight: bold; color: #1E3A8A;}
    .sub-header {font-size: 18px; font-weight: bold; color: #374151;}
    .card {background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom: 10px;}
    .metric-value {font-size: 28px; font-weight: bold;}
    .metric-label {font-size: 14px; color: #6B7280;}
</style>
""", unsafe_allow_html=True)

# --- KHỞI TẠO DỮ LIỆU GIẢ LẬP (MOCK DATA) ---
# Chuyển đổi từ constants.ts
def init_data():
    if 'stations' not in st.session_state:
        st.session_state['stations'] = [
            {
                "id": "1", "code": "QNHW002", "name": "Móng Cái", "region": "Miền Bắc", "status": "PLANNED",
                "province": "Quảng Ninh", "buildYear": "2026", "power": 60, "racks": 12,
                "manager": "Nguyễn Văn Quyền", "branchManager": "Nguyễn Văn Linh",
                "buildingType": "Cont", "category": "Quốc tế",
                "coordinates": {"lat": 21.521187, "lng": 107.961813},
                "designData": {
                    "racks": [{"id": "r1", "name": "Rack 1 (Nguồn)", "totalU": 42}],
                    "equipments": [],
                    "calcItems": [],
                    "costEstimateItems": [], # Dữ liệu dự toán
                    "roomParams": {"width": 3, "length": 5, "height": 3, "tempInside": 25, "tempOutside": 40, "equipmentHeatW": 0},
                    "batteryParams": {"dcLoadW": 0, "targetBackupTime": 8, "batteryVoltage": 48, "batteryAh": 100, "efficiency": 0.9},
                    "rectParams": {"dcLoadW": 0, "batteryAh": 0, "rectifierModuleSize": 3000}
                },
                "inventory": []
            },
            {
                "id": "2", "code": "NBHW001", "name": "Nam Định", "region": "Miền Bắc", "status": "ACTIVE",
                "province": "Ninh Bình", "buildYear": "2013", "power": 15, "racks": 5,
                "manager": "Nguyễn Văn Quyền", "branchManager": "Nguyễn Đình Dương",
                "buildingType": "Cont", "category": "Repeater",
                "coordinates": {"lat": 20.42027, "lng": 106.16459},
                "designData": {}, "inventory": []
            },
            {
                "id": "3", "code": "QNIW001", "name": "Ngọc Hồi", "region": "Miền Trung", "status": "ACTIVE",
                "province": "Quảng Ngãi", "buildYear": "2014", "power": 12, "racks": 5,
                "manager": "Nguyễn Duy Khánh", "branchManager": "Đinh Văn Thắng",
                "buildingType": "Cont", "category": "Repeater",
                "coordinates": {"lat": 14.704680, "lng": 107.685551},
                "designData": {}, "inventory": []
            },
             # ... (Bạn có thể thêm các trạm khác từ file constants.ts vào đây)
        ]
    
    if 'messages' not in st.session_state:
        st.session_state['messages'] = [{"role": "model", "parts": ["Xin chào! Tôi là trợ lý ảo PMB. Tôi có thể giúp gì cho bạn?"]}]

init_data()

# --- CÁC HÀM TIỆN ÍCH ---

def get_station_by_id(station_id):
    for s in st.session_state['stations']:
        if s['id'] == station_id:
            return s
    return None

def update_station(updated_station):
    for i, s in enumerate(st.session_state['stations']):
        if s['id'] == updated_station['id']:
            st.session_state['stations'][i] = updated_station
            return

# --- VIEW: DASHBOARD ---
def render_dashboard():
    st.markdown('<div class="main-header">Tổng quan hệ thống</div>', unsafe_allow_html=True)
    stations = st.session_state['stations']
    
    # Tính toán thống kê
    total = len(stations)
    active = len([s for s in stations if s['status'] == 'ACTIVE'])
    planned = len([s for s in stations if s['status'] == 'PLANNED'])
    offline = len([s for s in stations if s['status'] == 'OFFLINE'])
    maintenance = len([s for s in stations if s['status'] == 'MAINTENANCE'])
    total_power = sum([float(s.get('power', 0)) for s in stations])

    # Hiển thị Metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Tổng số trạm", total, delta="Trạm")
    with col2:
        st.metric("Đang hoạt động", active, delta=f"{round(active/total*100)}%", delta_color="normal")
    with col3:
        st.metric("Đang triển khai", planned, delta="Dự án mới")
    with col4:
        st.metric("Sự cố / Mất tín hiệu", offline, delta_color="inverse")
    with col5:
        st.metric("Tổng công suất", f"{total_power} kW")

    # Biểu đồ
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("Phân bố theo Khu vực")
        region_counts = pd.DataFrame(stations)['region'].value_counts().reset_index()
        region_counts.columns = ['Khu vực', 'Số lượng']
        fig_region = px.pie(region_counts, values='Số lượng', names='Khu vực', hole=0.4, color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig_region, use_container_width=True)

    with col_chart2:
        st.subheader("Công suất theo trạm")
        df_power = pd.DataFrame(stations).sort_values(by='power', ascending=False).head(10)
        fig_power = px.bar(df_power, x='name', y='power', color='status', title="Top 10 Trạm tiêu thụ điện năng",
                           labels={'power': 'Công suất (kW)', 'name': 'Tên trạm', 'status': 'Trạng thái'})
        st.plotly_chart(fig_power, use_container_width=True)

# --- VIEW: DANH SÁCH TRẠM ---
def render_station_list():
    st.markdown('<div class="main-header">Danh sách trạm tuyến trục</div>', unsafe_allow_html=True)
    
    # Filter
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_term = st.text_input("Tìm kiếm", placeholder="Nhập tên, mã trạm...")
    with col2:
        region_filter = st.selectbox("Khu vực", ["Tất cả", "Miền Bắc", "Miền Trung", "Miền Nam"])
    with col3:
        status_filter = st.selectbox("Trạng thái", ["Tất cả", "ACTIVE", "PLANNED", "MAINTENANCE", "OFFLINE"])

    # Xử lý lọc dữ liệu
    df = pd.DataFrame(st.session_state['stations'])
    
    if search_term:
        df = df[df['name'].str.contains(search_term, case=False) | df['code'].str.contains(search_term, case=False)]
    if region_filter != "Tất cả":
        df = df[df['region'] == region_filter]
    if status_filter != "Tất cả":
        df = df[df['status'] == status_filter]

    # Hiển thị bảng (Chỉ chọn các cột quan trọng)
    display_cols = ['code', 'name', 'province', 'region', 'status', 'power', 'buildingType', 'manager']
    
    st.dataframe(
        df[display_cols],
        column_config={
            "code": "Mã trạm",
            "name": "Tên trạm",
            "province": "Tỉnh/TP",
            "region": "Khu vực",
            "status": st.column_config.SelectboxColumn("Trạng thái", options=["ACTIVE", "PLANNED", "OFFLINE"], required=True),
            "power": st.column_config.NumberColumn("Công suất (kW)", format="%d kW"),
            "buildingType": "Loại nhà",
            "manager": "Nhân sự PMB"
        },
        use_container_width=True,
        hide_index=True
    )

    # Nút thêm mới (Mockup)
    if st.button("➕ Thêm trạm mới"):
        st.info("Chức năng thêm trạm đang được phát triển.")

# --- VIEW: TRỢ LÝ AI ---
def render_ai_assistant():
    st.markdown('<div class="main-header">Trợ lý ảo AI (Gemini)</div>', unsafe_allow_html=True)
    
    # Sidebar config API Key
    api_key = os.getenv("API_KEY") 
    if not api_key:
        api_key = st.sidebar.text_input("Nhập Google API Key", type="password")
    
    if not api_key:
        st.warning("Vui lòng nhập API Key để sử dụng AI.")
        return

    # Khởi tạo Chat
    genai.configure(api_key=api_key)
    
    # Chuẩn bị dữ liệu context cho AI
    stations_json = json.dumps(st.session_state['stations'], ensure_ascii=False)
    system_instruction = f"""
    Bạn là trợ lý ảo quản lý trạm viễn thông PMB. Dưới đây là dữ liệu các trạm:
    {stations_json}
    Hãy trả lời câu hỏi dựa trên dữ liệu này. Trả lời ngắn gọn, chuyên nghiệp.
    """
    
    model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_instruction)

    # Hiển thị lịch sử chat
    for msg in st.session_state['messages']:
        with st.chat_message(msg['role']):
            st.markdown(msg['parts'][0])

    # Input chat
    if prompt := st.chat_input("Hỏi gì đó về các trạm..."):
        # User message
        st.chat_message("user").markdown(prompt)
        st.session_state['messages'].append({"role": "user", "parts": [prompt]})
        
        # AI Response
        try:
            response = model.generate_content(prompt)
            st.chat_message("model").markdown(response.text)
            st.session_state['messages'].append({"role": "model", "parts": [response.text]})
        except Exception as e:
            st.error(f"Lỗi kết nối AI: {e}")

# --- VIEW: TÍNH TOÁN THIẾT KẾ ---
def render_design_calculations():
    st.markdown('<div class="main-header">Tính toán thiết kế & Dự toán</div>', unsafe_allow_html=True)

    # 1. Chọn trạm để thiết kế
    station_names = {s['id']: f"{s['code']} - {s['name']}" for s in st.session_state['stations']}
    selected_id = st.selectbox("Chọn trạm làm việc:", options=list(station_names.keys()), format_func=lambda x: station_names[x])
    
    station = get_station_by_id(selected_id)
    if not station:
        st.error("Không tìm thấy trạm")
        return

    # Đảm bảo designData tồn tại
    if 'designData' not in station:
        station['designData'] = {
            "calcItems": [], 
            "costEstimateItems": [],
            "batteryParams": {"dcLoadW": 0, "targetBackupTime": 8, "batteryVoltage": 48, "batteryAh": 100, "efficiency": 0.9}
        }
    
    design_data = station['designData']

    # TABS
    tab1, tab2, tab3, tab4 = st.tabs(["⚡ Công suất", "🔋 Ắc quy", "💰 Dự toán", "❄️ Điều hòa"])

    # --- TAB 1: CÔNG SUẤT ---
    with tab1:
        st.subheader("Bảng tính toán công suất trạm")
        
        # Tạo DataFrame từ calcItems
        calc_items = design_data.get('calcItems', [])
        
        # Editor cho bảng công suất
        if not calc_items:
            # Dữ liệu mẫu nếu trống
            df_calc = pd.DataFrame([{
                "id": str(datetime.now().timestamp()),
                "name": "Thiết bị mẫu", "model": "", "quantity": 1, 
                "powerRatedW": 100, "voltage": 48, "current": 2.08,
                "wireSection": "2x4", "wireType": "1 pha 2 dây", "type": "DC", "note": ""
            }])
        else:
            df_calc = pd.DataFrame(calc_items)

        # Cấu hình cột hiển thị
        edited_df = st.data_editor(
            df_calc,
            num_rows="dynamic",
            column_config={
                "name": "Tên thiết bị",
                "model": "Model",
                "quantity": st.column_config.NumberColumn("Số lượng", min_value=0, step=1),
                "powerRatedW": st.column_config.NumberColumn("P danh định (W)", min_value=0),
                "voltage": st.column_config.NumberColumn("U (V)", min_value=0),
                "current": st.column_config.NumberColumn("I (A)", disabled=True), # Tính toán tự động
                "wireSection": "Tiết diện (mm2)",
                "wireType": st.column_config.SelectboxColumn(
                    "Loại dây",
                    options=[
                        "1 pha 2 dây: 2x... mm2 - Cu/PVC",
                        "1 pha 1 dây 1 x ... mm2 - Cu/PVC",
                        "3 pha 3 dây: 3x ... mm2- Cu/PVC/PVC",
                        "3 pha 4 dây 3x... + 1x... mm2 -Cu/PVC/PVC"
                    ]
                ),
                "type": st.column_config.SelectboxColumn("Loại", options=["DC", "AC", "PASSIVE"]),
                "note": "Ghi chú"
            },
            key=f"editor_power_{selected_id}"
        )

        # Logic tính toán lại dòng I và Tổng
        if not edited_df.empty:
            # Tự động tính I = P / U nếu U > 0
            edited_df['current'] = edited_df.apply(lambda x: round(x['powerRatedW'] / x['voltage'], 2) if x['voltage'] > 0 else 0, axis=1)
            edited_df['total_power'] = edited_df['quantity'] * edited_df['powerRatedW']
            
            # Lưu lại vào session state
            design_data['calcItems'] = edited_df.to_dict('records')
            
            # Hiển thị tổng
            total_load = edited_df['total_power'].sum()
            st.info(f"👉 TỔNG CÔNG SUẤT TRẠM: **{total_load:,.0f} W**")

            # Nút lưu
            if st.button("Lưu bảng công suất"):
                update_station(station)
                st.success("Đã lưu dữ liệu!")

    # --- TAB 2: ẮC QUY ---
    with tab2:
        st.subheader("Tính toán dung lượng Ắc quy")
        col_batt1, col_batt2 = st.columns(2)
        
        params = design_data.get('batteryParams', {})
        
        with col_batt1:
            dc_load = st.number_input("Công suất tải DC (W)", value=float(params.get('dcLoadW', 0)))
            backup_time = st.number_input("Thời gian backup (Giờ)", value=float(params.get('targetBackupTime', 8)))
            batt_voltage = st.number_input("Điện áp (V)", value=float(params.get('batteryVoltage', 48)))
        
        with col_batt2:
            batt_ah = st.selectbox("Dung lượng 1 tổ (Ah)", [50, 100, 150, 200], index=1)
            efficiency = st.number_input("Hệ số xả sâu", value=float(params.get('efficiency', 0.9)), max_value=1.0)

        # Tính toán
        if batt_voltage * efficiency > 0:
            total_ah_req = (dc_load * backup_time) / (batt_voltage * efficiency)
            num_strings = total_ah_req / batt_ah
            rec_strings = int(num_strings) + 1 if num_strings % 1 > 0 else int(num_strings)
        else:
            total_ah_req, num_strings, rec_strings = 0, 0, 0

        st.divider()
        st.write(f"Dung lượng yêu cầu: **{total_ah_req:.2f} Ah**")
        st.write(f"Số tổ cần thiết (lý thuyết): **{num_strings:.2f}**")
        st.success(f"📌 KHUYẾN NGHỊ: Trang bị **{rec_strings}** tổ ắc quy **{batt_ah}Ah**")

        # Lưu params
        if st.button("Lưu tính toán Ắc quy"):
            design_data['batteryParams'] = {
                "dcLoadW": dc_load, "targetBackupTime": backup_time,
                "batteryVoltage": batt_voltage, "batteryAh": batt_ah, "efficiency": efficiency
            }
            update_station(station)
            st.success("Đã lưu!")

    # --- TAB 3: DỰ TOÁN (Yêu cầu mới) ---
    with tab3:
        st.subheader("Dự toán thiết bị & vật tư")
        
        cost_items = design_data.get('costEstimateItems', [])
        if not cost_items:
             df_cost = pd.DataFrame(columns=['category', 'itemCode', 'itemName', 'unit', 'quantity', 'unitPrice', 'condition', 'note'])
        else:
             df_cost = pd.DataFrame(cost_items)

        # Phân loại hiển thị (Để đơn giản trong Streamlit, ta dùng 1 bảng chung nhưng có cột Category)
        st.info("💡 Category: MAIN = Vật tư chính (từ Rack), AUX = Vật tư phụ (Nhập tay)")
        
        edited_cost_df = st.data_editor(
            df_cost,
            num_rows="dynamic",
            column_config={
                "category": st.column_config.SelectboxColumn("Phân loại", options=["MAIN", "AUX"], required=True),
                "itemCode": "Mã vật tư",
                "itemName": "Tên vật tư",
                "unit": "Đơn vị",
                "quantity": st.column_config.NumberColumn("Số lượng", min_value=1),
                "unitPrice": st.column_config.NumberColumn("Đơn giá (VNĐ)", format="%d đ"),
                "condition": st.column_config.SelectboxColumn("Tình trạng", options=["Mới", "Sử dụng lại"]),
                "note": "Ghi chú"
            },
            key=f"editor_cost_{selected_id}"
        )

        if not edited_cost_df.empty:
            # Tính thành tiền
            edited_cost_df['total'] = edited_cost_df['quantity'] * edited_cost_df['unitPrice']
            grand_total = edited_cost_df['total'].sum()
            
            # Hiển thị tổng
            st.markdown(f"### 💰 TỔNG CỘNG DỰ TOÁN: :red[{grand_total:,.0f} VNĐ]")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("Lưu Dự toán"):
                    # Lưu lại dữ liệu, loại bỏ cột 'total' vì nó là calculated field
                    save_df = edited_cost_df.drop(columns=['total'], errors='ignore')
                    design_data['costEstimateItems'] = save_df.to_dict('records')
                    update_station(station)
                    st.success("Đã lưu bảng dự toán!")
            
            with col_btn2:
                if st.button("Đồng bộ sang danh sách Vật tư"):
                    # Logic đồng bộ
                    current_inv = station.get('inventory', [])
                    for _, row in edited_cost_df.iterrows():
                        new_item = {
                            "id": str(datetime.now().timestamp()) + row['itemCode'],
                            "itemCode": row['itemCode'],
                            "itemName": row['itemName'],
                            "quantity": row['quantity'],
                            "unit": row['unit'],
                            "type": "OFFLINE",
                            "status": "PLANNED",
                            "note": f"Đồng bộ từ dự toán. {row['note']}"
                        }
                        current_inv.append(new_item)
                    
                    station['inventory'] = current_inv
                    update_station(station)
                    st.success(f"Đã đồng bộ {len(edited_cost_df)} mục sang Inventory!")

    # --- TAB 4: ĐIỀU HÒA ---
    with tab4:
        st.write("Chức năng tính toán nhiệt đang phát triển...")

# --- VIEW: VẬT TƯ THIẾT BỊ ---
def render_inventory():
    st.markdown('<div class="main-header">Quản lý Vật tư thiết bị</div>', unsafe_allow_html=True)
    
    station_names = {s['id']: f"{s['code']} - {s['name']}" for s in st.session_state['stations']}
    selected_id = st.selectbox("Chọn trạm xem vật tư:", options=list(station_names.keys()), format_func=lambda x: station_names[x], key="inv_select")
    
    station = get_station_by_id(selected_id)
    inventory = station.get('inventory', [])
    
    if inventory:
        df_inv = pd.DataFrame(inventory)
        st.dataframe(df_inv, use_container_width=True)
    else:
        st.warning("Trạm này chưa có dữ liệu vật tư.")

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.header("PMB Manager")
    menu = st.radio(
        "Menu",
        ["Tổng quan", "Danh sách trạm", "Hồ sơ triển khai", "Vật tư thiết bị", "Tính toán thiết kế", "Trợ lý AI"]
    )
    
    st.divider()
    st.caption("PMB Core v2.4.0 (Python Edition)")

# --- ROUTING ---
if menu == "Tổng quan":
    render_dashboard()
elif menu == "Danh sách trạm":
    render_station_list()
elif menu == "Trợ lý AI":
    render_ai_assistant()
elif menu == "Tính toán thiết kế":
    render_design_calculations()
elif menu == "Vật tư thiết bị":
    render_inventory()
else:
    st.info(f"Chức năng **{menu}** đang được chuyển đổi sang Python.")