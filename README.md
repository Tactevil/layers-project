A Chicken Farm Management System

Problem Statement

Managing a poultry farm involves juggling many records:

    Multiple batches of chickens (layers and indigenous kienyeji) with different acquisition dates, costs, and mortality.

    Daily egg production in dozens.

    Feed consumption and its cost.

    Additional expenses (vaccines, medication, labour).

    Egg sales revenue.

    Customer orders and their status.

    Sale of spent hens.

 Doing this manually with spreadsheets is error‑prone and time‑consuming. There is a need for a simple, offline, single‑user system that centralises all records and provides a real‑time financial dashboard.
Solution Overview

This project provides a Python command‑line interface (CLI) that interacts with a SQLite database. It allows the farmer to:

    Add new chicken batches (layers or kienyeji).

    Record daily egg production in dozens.

    Log feed usage (type, quantity, cost per kg).
    
    Track other costs (vaccines, medication, labour).

    Record egg sales (dozens sold, price, customer).

    Place customer orders (with automatic price based on egg type).

    Mark a batch as “spent” when it stops laying.

    Sell spent hens and update the batch count.

  View a dashboard showing:

        Active chicken inventory.

        Total revenue, total costs (feed + other + purchase), and net profit.

        Pending customer orders.

        Egg production of the last 7 days.

All data is stored locally in a single layers.db SQLite file, making it portable and easy to back up.

Technologies Used:
    Technology	Purpose
    Python 3	- Core programming language
    SQLite3	- Embedded relational database (no external server required)
    datetime -	Handling dates for records and queries
    CLI -	Simple text‑based user interface

Database Schema

The system uses seven tables:

    batches – stores batch info (name, type, dates, counts, purchase cost, status).

    egg_production – daily egg counts (dozens) per batch.

    feed_usage – feed consumption records (type, kg, unit cost).

    other_costs – miscellaneous expenses (category, amount).

    egg_sales – sales records (dozens sold, price per dozen, customer).

    orders – customer orders (egg type, quantity, total price, order date, status).

    spent_sales – sales of spent hens (count, price per bird, buyer).

Foreign keys link egg production, feed usage, egg sales, and spent sales to the relevant batch.

Future Improvements

    Add a GUI (Tkinter or PyQt) for easier use.

    Implement data export to CSV/Excel.

    Add batch‑wise profit/loss analysis.

    Automatic calculation of feed conversion ratio (FCR).

    Notifications for low feed stock or expiring orders.

    User authentication (multi‑user support).
