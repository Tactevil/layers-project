import sqlite3
import datetime
import pandas as pd
import streamlit as st

# DATABASE SETUP
def setup_database():
    conn = sqlite3.connect("layers.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS batches(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            type TEXT,
            date_acquired TEXT,
            initial_count INTEGER,
            current_count INTEGER,
            purchase_cost REAL,
            status TEXT DEFAULT 'active'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS egg_production(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER,
            date TEXT,
            count_dozen INTEGER,
            FOREIGN KEY(batch_id) REFERENCES batches(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feed_usage(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER,
            date TEXT,
            feed_type TEXT,
            quantity_kg REAL,
            unit_cost REAL,
            FOREIGN KEY(batch_id) REFERENCES batches(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS other_costs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            category TEXT,
            amount REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS egg_sales(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER,
            date TEXT,
            quantity_dozen INTEGER,
            price_per_dozen REAL,
            customer_name TEXT,
            FOREIGN KEY(batch_id) REFERENCES batches(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            phone TEXT,
            egg_type TEXT,
            quantity_dozen INTEGER,
            total_price REAL,
            order_date TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spent_sales(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER,
            date TEXT,
            count_sold INTEGER,
            price_per_bird REAL,
            buyer_name TEXT,
            FOREIGN KEY(batch_id) REFERENCES batches(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

#  HELPER FUNCTIONS 
def get_connection():
    
    return sqlite3.connect("layers.db")

def get_active_batches():
    
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, name, type, current_count FROM batches WHERE status='active'", conn)
    conn.close()
    return df

def get_all_batches():
    
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM batches", conn)
    conn.close()
    return df

def get_batch_name(batch_id):
   
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM batches WHERE id=?", (batch_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "Unknown"

def delete_record(table, id_column, id_value):
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM {table} WHERE {id_column}=?", (id_value,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError as e:
        conn.close()
        st.error(f"Cannot delete: {e}. This record has related entries.")
        return False

# ---- ADDED: helper functions for update ----
def fetch_record(table, id_column, id_value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table} WHERE {id_column}=?", (id_value,))
    row = cursor.fetchone()
    conn.close()
    if row:
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    return None

def update_record(table, id_column, id_value, update_dict):
    if not update_dict:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    set_clause = ", ".join([f"{col}=?" for col in update_dict.keys()])
    values = list(update_dict.values()) + [id_value]
    query = f"UPDATE {table} SET {set_clause} WHERE {id_column}=?"
    try:
        cursor.execute(query, values)
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        conn.close()
        st.error(f"Update failed: {e}")
        return False

#  safe date parser 
def safe_parse_date(date_str):
    try:
        return pd.to_datetime(date_str).date()
    except Exception:
        #  try to parse manually if pd.to_datetime fails
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

#  STREAMLIT MAIN APP 
def main():
    st.set_page_config(page_title="Layer Farm Manager", layout="wide")
    st.title("Layer Farm Management")

    setup_database()  

    #  sidebar navigation instead of CLI menu loop
    menu = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Batches", "Egg Production", "Feed Usage", "Other Costs",
         "Egg Sales", "Orders", "Spent Hens Sales"]
    )

    # DASHBOARD 
    if menu == "Dashboard":
        st.header(" Dashboard")
        conn = get_connection()

        # Active chickens
        inventory_df = pd.read_sql_query(
            "SELECT type, SUM(current_count) as count FROM batches WHERE status='active' GROUP BY type", conn
        )
        if not inventory_df.empty:
            st.subheader("Active Chickens")
            st.dataframe(inventory_df)

        # Revenue & costs
        revenue_df = pd.read_sql_query("SELECT SUM(quantity_dozen * price_per_dozen) as revenue FROM egg_sales", conn)
        revenue = revenue_df.iloc[0]['revenue'] if not revenue_df.empty and revenue_df.iloc[0]['revenue'] else 0

        feed_cost_df = pd.read_sql_query("SELECT SUM(quantity_kg * unit_cost) as cost FROM feed_usage", conn)
        feed_cost = feed_cost_df.iloc[0]['cost'] if not feed_cost_df.empty and feed_cost_df.iloc[0]['cost'] else 0
        other_cost_df = pd.read_sql_query("SELECT SUM(amount) as cost FROM other_costs", conn)
        other_cost = other_cost_df.iloc[0]['cost'] if not other_cost_df.empty and other_cost_df.iloc[0]['cost'] else 0
        purchase_cost_df = pd.read_sql_query("SELECT SUM(purchase_cost) as cost FROM batches", conn)
        purchase_cost = purchase_cost_df.iloc[0]['cost'] if not purchase_cost_df.empty and purchase_cost_df.iloc[0]['cost'] else 0

        total_costs = feed_cost + other_cost + purchase_cost
        profit = revenue - total_costs

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Revenue (Egg Sales)", f"KSH {revenue:,.2f}")
        col2.metric("Total Costs", f"KSH {total_costs:,.2f}")
        col3.metric("Net Profit", f"KSH {profit:,.2f}")
        # safer pending orders count
        pending_count = pd.read_sql_query("SELECT COUNT(*) FROM orders WHERE status='pending'", conn).iloc[0,0]
        col4.metric("Pending Orders", value=pending_count)

        # Recent production
        st.subheader("Recent Egg Production (Last 7 days)")
        recent_df = pd.read_sql_query("""
            SELECT b.name, SUM(e.count_dozen) as dozens
            FROM egg_production e
            JOIN batches b ON e.batch_id = b.id
            WHERE e.date >= date('now', '-7 days')
            GROUP BY b.name
        """, conn)
        if not recent_df.empty:
            st.dataframe(recent_df)
        else:
            st.info("No eggs recorded in the last 7 days.")
        conn.close()

    # BATCHES 
    elif menu == "Batches":
        st.header("Batches")

        #  SEARCH & FILTER
        st.subheader("Search & Filter")
        col_search, col_status = st.columns(2)
        with col_search:
            search = st.text_input("Search by name", "")
        with col_status:
            status_filter = st.selectbox("Status", ["All", "active", "spent"])

        # : Form for adding a batch function)
        with st.expander("Add New Batch"):
            with st.form("add_batch"):
                name = st.text_input("Batch Name")
                b_type = st.selectbox("Type", ["layers", "kienyeji"])
                date = st.date_input("Date Acquired", value=datetime.date.today())
                initial_count = st.number_input("Initial Count", min_value=1, step=1)
                purchase_cost = st.number_input("Purchase Cost (KSH)", min_value=0.0, step=100.0)
                submitted = st.form_submit_button("Add Batch")
                if submitted:
                    #  input validation 
                    if not name:
                        st.error("Batch name is required.")
                    else:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO batches (name, type, date_acquired, initial_count, current_count, purchase_cost)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (name, b_type, date.isoformat(), initial_count, initial_count, purchase_cost))
                        conn.commit()
                        conn.close()
                        st.success("Batch added successfully!")
                        st.rerun()

        #  View all batches with search and status filter
        st.subheader("All Batches")
        df = get_all_batches()
        if search:
            df = df[df['name'].str.contains(search, case=False, na=False)]
        if status_filter != "All":
            df = df[df['status'] == status_filter]
        st.dataframe(df, use_container_width=True)

        # UPDATE BATCH
        st.subheader("Update Batch")
        batch_id_to_update = st.number_input("Batch ID to update", min_value=1, step=1, key="batch_update_id")
        if batch_id_to_update:
            record = fetch_record("batches", "id", batch_id_to_update)
            if record:
                with st.form("update_batch"):
                    new_name = st.text_input("Name", value=record['name'])
                    new_type = st.selectbox("Type", ["layers", "kienyeji"], index=0 if record['type']=="layers" else 1)
                    new_date = st.date_input("Date Acquired", value=safe_parse_date(record['date_acquired']))
                    new_initial = st.number_input("Initial Count", value=record['initial_count'], step=1)
                    new_current = st.number_input("Current Count", value=record['current_count'], step=1)
                    new_cost = st.number_input("Purchase Cost (KSH)", value=record['purchase_cost'], step=100.0)
                    new_status = st.selectbox("Status", ["active", "spent"], index=0 if record['status']=="active" else 1)
                    update_submitted = st.form_submit_button("Update Batch")
                    if update_submitted:
                        update_dict = {
                            'name': new_name,
                            'type': new_type,
                            'date_acquired': new_date.isoformat(),
                            'initial_count': new_initial,
                            'current_count': new_current,
                            'purchase_cost': new_cost,
                            'status': new_status
                        }
                        if update_record("batches", "id", batch_id_to_update, update_dict):
                            st.success("Batch updated successfully!")
                            st.rerun()
            else:
                st.warning("Batch ID not found.")

        #  Delete batch with dependency check 
        st.subheader("Delete Batch")
        batch_id_to_delete = st.number_input("Batch ID to delete", min_value=1, step=1, key="batch_delete_id")
        if st.button("Delete Batch"):
            # Check dependencies
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM egg_production WHERE batch_id=?", (batch_id_to_delete,))
            egg_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM feed_usage WHERE batch_id=?", (batch_id_to_delete,))
            feed_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM egg_sales WHERE batch_id=?", (batch_id_to_delete,))
            sales_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM spent_sales WHERE batch_id=?", (batch_id_to_delete,))
            spent_count = cursor.fetchone()[0]
            conn.close()

            if egg_count + feed_count + sales_count + spent_count > 0:
                st.warning(f"This batch has {egg_count} egg records, {feed_count} feed records, {sales_count} sales, {spent_count} spent sales. Deleting will remove all related data (CASCADE).")
                if st.checkbox("I understand, delete anyway"):
                    conn = get_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute("DELETE FROM batches WHERE id=?", (batch_id_to_delete,))
                        conn.commit()
                        st.success("Batch deleted successfully.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Cannot delete due to foreign key constraints.")
                    finally:
                        conn.close()
            else:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM batches WHERE id=?", (batch_id_to_delete,))
                conn.commit()
                conn.close()
                st.success("Batch deleted successfully.")
                st.rerun()

    # EGG PRODUCTION
    elif menu == "Egg Production":
        st.header("Egg Production")

        # SEARCH & FILTER
        st.subheader("Search & Filter")
        conn = get_connection()
        all_batches = pd.read_sql_query("SELECT DISTINCT name FROM batches", conn)
        conn.close()
        batch_list = ["All"] + list(all_batches['name'])
        col_batch, col_date = st.columns(2)
        with col_batch:
            batch_filter = st.selectbox("Filter by Batch", batch_list)
        with col_date:
            date_range = st.date_input("Date Range", [])

        with st.expander("Record Daily Eggs"):
            df_batches = get_active_batches()
            if df_batches.empty:
                st.warning("No active batches. Add a batch first.")
            else:
                with st.form("add_eggs"):
                    batch_id = st.selectbox("Batch", df_batches['id'], format_func=lambda x: f"{x} - {df_batches[df_batches['id']==x]['name'].iloc[0]}")
                    date = st.date_input("Date", value=datetime.date.today())
                    dozens = st.number_input("Dozens Collected", min_value=0, step=1)
                    submitted = st.form_submit_button("Record")
                    if submitted:
                        #  validation 
                        if dozens <= 0:
                            st.error("Enter a positive number of dozens.")
                        else:
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO egg_production (batch_id, date, count_dozen) VALUES (?, ?, ?)",
                                           (batch_id, date.isoformat(), dozens))
                            conn.commit()
                            conn.close()
                            st.success("Eggs recorded!")
                            st.rerun()

        st.subheader("Egg Production Records")
        conn = get_connection()
        df = pd.read_sql_query("""
            SELECT e.id, b.name as batch, e.date, e.count_dozen
            FROM egg_production e
            JOIN batches b ON e.batch_id = b.id
        """, conn)
        conn.close()
        if not df.empty:
            #batch filter and date range filter
            if batch_filter != "All":
                df = df[df['batch'] == batch_filter]
            if len(date_range) == 2:
                df = df[(df['date'] >= date_range[0].isoformat()) & (df['date'] <= date_range[1].isoformat())]
            st.dataframe(df, use_container_width=True)

            # UPDATE EGG PRODUCTION
            st.subheader("Update Record")
            rec_id = st.number_input("Record ID to update", min_value=1, step=1, key="egg_update_id")
            if rec_id:
                record = fetch_record("egg_production", "id", rec_id)
                if record:
                    with st.form("update_egg"):
                        conn = get_connection()
                        batches = pd.read_sql_query("SELECT id, name FROM batches", conn)
                        conn.close()
                        batch_options = batches['id'].tolist()
                        batch_labels = {row['id']: f"{row['id']} - {row['name']}" for _, row in batches.iterrows()}
                        new_batch = st.selectbox("Batch", batch_options, format_func=lambda x: batch_labels.get(x, x), index=batch_options.index(record['batch_id']))
                        new_date = st.date_input("Date", value=safe_parse_date(record['date']))
                        new_dozens = st.number_input("Dozens Collected", value=record['count_dozen'], step=1)
                        update_submitted = st.form_submit_button("Update Record")
                        if update_submitted:
                            if new_dozens <= 0:
                                st.error("Dozens must be positive.")
                            else:
                                update_dict = {
                                    'batch_id': new_batch,
                                    'date': new_date.isoformat(),
                                    'count_dozen': new_dozens
                                }
                                if update_record("egg_production", "id", rec_id, update_dict):
                                    st.success("Record updated!")
                                    st.rerun()
                else:
                    st.warning("Record ID not found.")

            #  delete record
            st.subheader("Delete Record")
            rec_id_del = st.number_input("Record ID to delete", min_value=1, step=1)
            if st.button("Delete Record"):
                if delete_record("egg_production", "id", rec_id_del):
                    st.success("Record deleted.")
                    st.rerun()
        else:
            st.info("No records found.")

    # FEED USAGE
    elif menu == "Feed Usage":
        st.header(" Feed Usage")

        # SEARCH
        st.subheader("Search")
        search_feed = st.text_input("Search by feed type")

        with st.expander("Record Feed Usage"):
            df_batches = get_active_batches()
            if df_batches.empty:
                st.warning("No active batches.")
            else:
                with st.form("add_feed"):
                    batch_id = st.selectbox("Batch", df_batches['id'], format_func=lambda x: f"{x} - {df_batches[df_batches['id']==x]['name'].iloc[0]}")
                    date = st.date_input("Date", value=datetime.date.today())
                    feed_type = st.text_input("Feed Type (e.g., layers mash)")
                    quantity_kg = st.number_input("Quantity (kg)", min_value=0.0, step=0.5)
                    unit_cost = st.number_input("Cost per kg (KSH)", min_value=0.0, step=1.0)
                    submitted = st.form_submit_button("Record")
                    if submitted:
                        # validation
                        if not feed_type or quantity_kg <= 0 or unit_cost <= 0:
                            st.error("All fields are required and must be positive.")
                        else:
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO feed_usage (batch_id, date, feed_type, quantity_kg, unit_cost) VALUES (?, ?, ?, ?, ?)",
                                           (batch_id, date.isoformat(), feed_type, quantity_kg, unit_cost))
                            conn.commit()
                            conn.close()
                            st.success("Feed usage recorded.")
                            st.rerun()

        st.subheader("Feed Usage Records")
        conn = get_connection()
        df = pd.read_sql_query("""
            SELECT f.id, b.name as batch, f.date, f.feed_type, f.quantity_kg, f.unit_cost,
                   (f.quantity_kg * f.unit_cost) as total_cost
            FROM feed_usage f
            JOIN batches b ON f.batch_id = b.id
        """, conn)
        conn.close()
        if not df.empty:
            # search by feed type
            if search_feed:
                df = df[df['feed_type'].str.contains(search_feed, case=False, na=False)]
            st.dataframe(df, use_container_width=True)

            #UPDATE FEED 
            st.subheader("Update Feed Record")
            rec_id = st.number_input("Feed Record ID to update", min_value=1, step=1, key="feed_update_id")
            if rec_id:
                record = fetch_record("feed_usage", "id", rec_id)
                if record:
                    with st.form("update_feed"):
                        conn = get_connection()
                        batches = pd.read_sql_query("SELECT id, name FROM batches", conn)
                        conn.close()
                        batch_options = batches['id'].tolist()
                        batch_labels = {row['id']: f"{row['id']} - {row['name']}" for _, row in batches.iterrows()}
                        new_batch = st.selectbox("Batch", batch_options, format_func=lambda x: batch_labels.get(x, x), index=batch_options.index(record['batch_id']))
                        new_date = st.date_input("Date", value=safe_parse_date(record['date']))
                        new_feed_type = st.text_input("Feed Type", value=record['feed_type'])
                        new_quantity = st.number_input("Quantity (kg)", value=record['quantity_kg'], step=0.5)
                        new_unit_cost = st.number_input("Cost per kg (KSH)", value=record['unit_cost'], step=1.0)
                        update_submitted = st.form_submit_button("Update Record")
                        if update_submitted:
                            if not new_feed_type or new_quantity <= 0 or new_unit_cost <= 0:
                                st.error("All fields must be filled with positive numbers.")
                            else:
                                update_dict = {
                                    'batch_id': new_batch,
                                    'date': new_date.isoformat(),
                                    'feed_type': new_feed_type,
                                    'quantity_kg': new_quantity,
                                    'unit_cost': new_unit_cost
                                }
                                if update_record("feed_usage", "id", rec_id, update_dict):
                                    st.success("Feed record updated!")
                                    st.rerun()
                else:
                    st.warning("Record ID not found.")

            # delete record
            rec_id_del = st.number_input("Feed Record ID to delete", min_value=1, step=1)
            if st.button("Delete Feed Record"):
                if delete_record("feed_usage", "id", rec_id_del):
                    st.success("Deleted.")
                    st.rerun()
        else:
            st.info("No feed records.")

    # OTHER COSTS 
    elif menu == "Other Costs":
        st.header("Other Costs")

        # SEARCH 
        st.subheader("Search")
        search_cost = st.text_input("Search by category")

        with st.expander("Add Other Cost"):
            with st.form("add_cost"):
                date = st.date_input("Date", value=datetime.date.today())
                category = st.text_input("Category (e.g., vaccines, medications, labor)")
                amount = st.number_input("Amount (KSH)", min_value=0.0, step=100.0)
                submitted = st.form_submit_button("Add Cost")
                if submitted:
                    if not category or amount <= 0:
                        st.error("Please fill all fields with positive amount.")
                    else:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO other_costs (date, category, amount) VALUES (?, ?, ?)",
                                       (date.isoformat(), category, amount))
                        conn.commit()
                        conn.close()
                        st.success("Cost added.")
                        st.rerun()

        st.subheader("Other Costs Records")
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM other_costs", conn)
        conn.close()
        if not df.empty:
            #  search by category
            if search_cost:
                df = df[df['category'].str.contains(search_cost, case=False, na=False)]
            st.dataframe(df, use_container_width=True)

            # UPDATE OTHER COST
            st.subheader("Update Cost Record")
            rec_id = st.number_input("Cost Record ID to update", min_value=1, step=1, key="cost_update_id")
            if rec_id:
                record = fetch_record("other_costs", "id", rec_id)
                if record:
                    with st.form("update_cost"):
                        new_date = st.date_input("Date", value=safe_parse_date(record['date']))
                        new_category = st.text_input("Category", value=record['category'])
                        new_amount = st.number_input("Amount (KSH)", value=record['amount'], step=100.0)
                        update_submitted = st.form_submit_button("Update Record")
                        if update_submitted:
                            if not new_category or new_amount <= 0:
                                st.error("Category and positive amount required.")
                            else:
                                update_dict = {
                                    'date': new_date.isoformat(),
                                    'category': new_category,
                                    'amount': new_amount
                                }
                                if update_record("other_costs", "id", rec_id, update_dict):
                                    st.success("Cost record updated!")
                                    st.rerun()
                else:
                    st.warning("Record ID not found.")

            # delete record
            rec_id_del = st.number_input("Cost Record ID to delete", min_value=1, step=1)
            if st.button("Delete Cost Record"):
                if delete_record("other_costs", "id", rec_id_del):
                    st.success("Deleted.")
                    st.rerun()
        else:
            st.info("No other costs recorded.")

    #  EGG SALES
    elif menu == "Egg Sales":
        st.header("Egg Sales")

        #  SEARCH
        st.subheader("Search")
        search_customer = st.text_input("Search by customer")

        with st.expander("Record Egg Sale"):
            df_batches = get_active_batches()
            if df_batches.empty:
                st.warning("No active batches.")
            else:
                with st.form("add_sale"):
                    batch_id = st.selectbox("Batch", df_batches['id'], format_func=lambda x: f"{x} - {df_batches[df_batches['id']==x]['name'].iloc[0]}")
                    date = st.date_input("Date", value=datetime.date.today())
                    dozens = st.number_input("Dozens Sold", min_value=1, step=1)
                    price = st.number_input("Price per Dozen (KSH)", min_value=0.0, step=10.0)
                    customer = st.text_input("Customer Name (optional)")
                    submitted = st.form_submit_button("Record Sale")
                    if submitted:
                        if dozens <= 0 or price <= 0:
                            st.error("Enter positive values.")
                        else:
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO egg_sales (batch_id, date, quantity_dozen, price_per_dozen, customer_name) VALUES (?, ?, ?, ?, ?)",
                                           (batch_id, date.isoformat(), dozens, price, customer or "Walk-in"))
                            conn.commit()
                            conn.close()
                            st.success("Sale recorded.")
                            st.rerun()

        st.subheader("Egg Sales Records")
        conn = get_connection()
        df = pd.read_sql_query("""
            SELECT s.id, b.name as batch, s.date, s.quantity_dozen, s.price_per_dozen,
                   (s.quantity_dozen * s.price_per_dozen) as total, s.customer_name
            FROM egg_sales s
            JOIN batches b ON s.batch_id = b.id
        """, conn)
        conn.close()
        if not df.empty:
            # search by customer
            if search_customer:
                df = df[df['customer_name'].str.contains(search_customer, case=False, na=False)]
            st.dataframe(df, use_container_width=True)

            # UPDATE EGG SALE
            st.subheader("Update Sale Record")
            rec_id = st.number_input("Sale Record ID to update", min_value=1, step=1, key="sale_update_id")
            if rec_id:
                record = fetch_record("egg_sales", "id", rec_id)
                if record:
                    with st.form("update_sale"):
                        conn = get_connection()
                        batches = pd.read_sql_query("SELECT id, name FROM batches", conn)
                        conn.close()
                        batch_options = batches['id'].tolist()
                        batch_labels = {row['id']: f"{row['id']} - {row['name']}" for _, row in batches.iterrows()}
                        new_batch = st.selectbox("Batch", batch_options, format_func=lambda x: batch_labels.get(x, x), index=batch_options.index(record['batch_id']))
                        new_date = st.date_input("Date", value=safe_parse_date(record['date']))
                        new_dozens = st.number_input("Dozens Sold", value=record['quantity_dozen'], step=1)
                        new_price = st.number_input("Price per Dozen (KSH)", value=record['price_per_dozen'], step=10.0)
                        new_customer = st.text_input("Customer Name", value=record['customer_name'] or "")
                        update_submitted = st.form_submit_button("Update Record")
                        if update_submitted:
                            if new_dozens <= 0 or new_price <= 0:
                                st.error("Positive values required.")
                            else:
                                update_dict = {
                                    'batch_id': new_batch,
                                    'date': new_date.isoformat(),
                                    'quantity_dozen': new_dozens,
                                    'price_per_dozen': new_price,
                                    'customer_name': new_customer or "Walk-in"
                                }
                                if update_record("egg_sales", "id", rec_id, update_dict):
                                    st.success("Sale record updated!")
                                    st.rerun()
                else:
                    st.warning("Record ID not found.")

            # delete record
            rec_id_del = st.number_input("Sale Record ID to delete", min_value=1, step=1)
            if st.button("Delete Sale Record"):
                if delete_record("egg_sales", "id", rec_id_del):
                    st.success("Deleted.")
                    st.rerun()
        else:
            st.info("No sales records.")

    # ORDERS
    elif menu == "Orders":
        st.header("Customer Orders")

        # SEARCH & FILTER
        st.subheader("Search & Filter")
        col_search_order, col_status_order = st.columns(2)
        with col_search_order:
            search_order = st.text_input("Search by customer")
        with col_status_order:
            status_filter_order = st.selectbox("Status", ["All", "pending", "paid", "delivered"])

        with st.expander("Place New Order"):
            with st.form("add_order"):
                customer = st.text_input("Customer Name")
                phone = st.text_input("Phone Number")
                egg_type = st.selectbox("Egg Type", ["layers", "kienyeji"])
                dozens = st.number_input("Quantity (dozens)", min_value=1, step=1)
                price_per_dozen = 400 if egg_type == "layers" else 750
                total_price = dozens * price_per_dozen
                st.write(f"Total Price: KSH {total_price}")
                submitted = st.form_submit_button("Place Order")
                if submitted:
                    if not customer or not phone or dozens <= 0:
                        st.error("Please fill all fields.")
                    else:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO orders (customer_name, phone, egg_type, quantity_dozen, total_price, order_date)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (customer, phone, egg_type, dozens, total_price, datetime.date.today().isoformat()))
                        conn.commit()
                        conn.close()
                        st.success(f"Order placed! Total: KSH {total_price}")
                        st.rerun()

        st.subheader("All Orders")
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM orders", conn)
        conn.close()
        if not df.empty:
            # search by customer and status filter
            if search_order:
                df = df[df['customer_name'].str.contains(search_order, case=False, na=False)]
            if status_filter_order != "All":
                df = df[df['status'] == status_filter_order]
            st.dataframe(df, use_container_width=True)

            #UPDATE ORDER
            st.subheader("Update Order")
            order_id = st.number_input("Order ID", min_value=1, step=1, key="order_update_id")
            if order_id:
                record = fetch_record("orders", "id", order_id)
                if record:
                    with st.form("update_order"):
                        new_customer = st.text_input("Customer Name", value=record['customer_name'])
                        new_phone = st.text_input("Phone", value=record['phone'])
                        new_egg_type = st.selectbox("Egg Type", ["layers", "kienyeji"], index=0 if record['egg_type']=="layers" else 1)
                        new_dozens = st.number_input("Quantity (dozens)", value=record['quantity_dozen'], step=1)
                        price_per_dozen_new = 400 if new_egg_type == "layers" else 750
                        new_total = new_dozens * price_per_dozen_new
                        st.write(f"New Total Price: KSH {new_total}")
                        new_status = st.selectbox("Status", ["pending", "paid", "delivered"], index=["pending","paid","delivered"].index(record['status']))
                        update_submitted = st.form_submit_button("Update Order")
                        if update_submitted:
                            if not new_customer or not new_phone or new_dozens <= 0:
                                st.error("All fields required and quantity positive.")
                            else:
                                update_dict = {
                                    'customer_name': new_customer,
                                    'phone': new_phone,
                                    'egg_type': new_egg_type,
                                    'quantity_dozen': new_dozens,
                                    'total_price': new_total,
                                    'status': new_status
                                }
                                if update_record("orders", "id", order_id, update_dict):
                                    st.success("Order updated!")
                                    st.rerun()
                else:
                    st.warning("Order ID not found.")

            # delete record
            rec_id_del = st.number_input("Order ID to delete", min_value=1, step=1, key="del_order")
            if st.button("Delete Order"):
                if delete_record("orders", "id", rec_id_del):
                    st.success("Order deleted.")
                    st.rerun()
        else:
            st.info("No orders.")

    # SPENT HENS SALES 
    elif menu == "Spent Hens Sales":
        st.header("Spent Hens Sales")

        # SEARCH 
        st.subheader("Search")
        search_buyer = st.text_input("Search by buyer")

        conn = get_connection()
        spent_df = pd.read_sql_query("SELECT id, name, current_count FROM batches WHERE status='spent' AND current_count>0", conn)
        conn.close()
        if spent_df.empty:
            st.warning("No spent batches with available birds.")
        else:
            with st.expander("Sell Spent Hens"):
                with st.form("sell_spent"):
                    batch_id = st.selectbox("Batch", spent_df['id'], format_func=lambda x: f"{x} - {spent_df[spent_df['id']==x]['name'].iloc[0]} (Available: {spent_df[spent_df['id']==x]['current_count'].iloc[0]})")
                    count = st.number_input("Number of birds sold", min_value=1, step=1)
                    price = st.number_input("Price per bird (KSH)", min_value=0.0, step=50.0)
                    buyer = st.text_input("Buyer Name (optional)")
                    date = st.date_input("Date", value=datetime.date.today())
                    submitted = st.form_submit_button("Record Sale")
                    if submitted:
                        # validation for available count
                        available = spent_df[spent_df['id']==batch_id]['current_count'].iloc[0]
                        if count > available:
                            st.error(f"Only {available} birds available.")
                        elif price <= 0:
                            st.error("Price must be positive.")
                        else:
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO spent_sales (batch_id, date, count_sold, price_per_bird, buyer_name) VALUES (?, ?, ?, ?, ?)",
                                           (batch_id, date.isoformat(), count, price, buyer or "Walk-in"))
                            cursor.execute("UPDATE batches SET current_count = current_count - ? WHERE id = ?", (count, batch_id))
                            conn.commit()
                            conn.close()
                            st.success("Spent hen sale recorded.")
                            st.rerun()

        st.subheader("Spent Hens Sales Records")
        conn = get_connection()
        df = pd.read_sql_query("""
            SELECT s.id, b.name as batch, s.date, s.count_sold, s.price_per_bird,
                   (s.count_sold * s.price_per_bird) as total, s.buyer_name
            FROM spent_sales s
            JOIN batches b ON s.batch_id = b.id
        """, conn)
        conn.close()
        if not df.empty:
            # search by buyer
            if search_buyer:
                df = df[df['buyer_name'].str.contains(search_buyer, case=False, na=False)]
            st.dataframe(df, use_container_width=True)

            # UPDATE SPENT SALE
            st.subheader("Update Spent Sale Record")
            rec_id = st.number_input("Spent Sale Record ID to update", min_value=1, step=1, key="spent_update_id")
            if rec_id:
                record = fetch_record("spent_sales", "id", rec_id)
                if record:
                    with st.form("update_spent"):
                        conn = get_connection()
                        batches = pd.read_sql_query("SELECT id, name FROM batches", conn)
                        conn.close()
                        batch_options = batches['id'].tolist()
                        batch_labels = {row['id']: f"{row['id']} - {row['name']}" for _, row in batches.iterrows()}
                        new_batch = st.selectbox("Batch", batch_options, format_func=lambda x: batch_labels.get(x, x), index=batch_options.index(record['batch_id']))
                        new_date = st.date_input("Date", value=safe_parse_date(record['date']))
                        new_count = st.number_input("Number of birds sold", value=record['count_sold'], step=1)
                        new_price = st.number_input("Price per bird (KSH)", value=record['price_per_bird'], step=50.0)
                        new_buyer = st.text_input("Buyer Name", value=record['buyer_name'] or "")
                        update_submitted = st.form_submit_button("Update Record")
                        if update_submitted:
                            if new_count <= 0 or new_price <= 0:
                                st.error("Positive values required.")
                            else:
                                update_dict = {
                                    'batch_id': new_batch,
                                    'date': new_date.isoformat(),
                                    'count_sold': new_count,
                                    'price_per_bird': new_price,
                                    'buyer_name': new_buyer or "Walk-in"
                                }
                                if update_record("spent_sales", "id", rec_id, update_dict):
                                    st.success("Spent sale record updated! (Batch count not automatically adjusted – please adjust manually if needed.)")
                                    st.rerun()
                else:
                    st.warning("Record ID not found.")

            # delete record
            rec_id_del = st.number_input("Spent Sale Record ID to delete", min_value=1, step=1)
            if st.button("Delete Spent Sale Record"):
                if delete_record("spent_sales", "id", rec_id_del):
                    st.success("Deleted. You may need to manually adjust batch count if needed.")
                    st.rerun()
        else:
            st.info("No spent hen sales records.")

if __name__ == "__main__":
    main()