#!/usr/bin/env python3
"""
Flight Ticket Booking System (CLI)
Features:
- User registration & login (password hashed)
- Flight search (by source, destination, date)
- Seat selection with seat map
- Booking management (create, view, cancel)
- Fare calculation (base fare + taxes/fees)
- Data storage using SQLite (persistent)
- Simple input validation and user-friendly CLI
"""

import sqlite3
import hashlib
import getpass
import os
import sys
import datetime
import random
import textwrap

DB_PATH = os.path.join(os.path.expanduser("~"), "flight_booking.db")


# Utilities

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def now_str():
    return datetime.datetime.now().isoformat(sep=" ", timespec="seconds")


def clear_console():
    os.system("cls" if os.name == "nt" else "clear")


def input_hidden(prompt="Password: "):
    try:
        return getpass.getpass(prompt)
    except Exception:
        return input(prompt)


# Database layer

class DB:
    def __init__(self, path=DB_PATH):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._seed_flights_if_empty()

    def _create_tables(self):
        c = self.conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS flights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flight_no TEXT NOT NULL,
                src TEXT NOT NULL,
                dst TEXT NOT NULL,
                depart_date TEXT NOT NULL,        -- YYYY-MM-DD
                depart_time TEXT NOT NULL,        -- HH:MM
                duration_minutes INTEGER NOT NULL,
                base_fare REAL NOT NULL,
                total_seats INTEGER NOT NULL
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_ref TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                flight_id INTEGER NOT NULL,
                seat TEXT NOT NULL,
                fare REAL NOT NULL,
                status TEXT NOT NULL,            -- BOOKED / CANCELED
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(flight_id) REFERENCES flights(id)
            )"""
        )
        self.conn.commit()

    def _seed_flights_if_empty(self):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM flights")
        count = c.fetchone()[0]
        if count == 0:
            # Seed sample flights for upcoming dates
            today = datetime.date.today()
            sample = [
                ("DG101", "Coimbatore", "Bengaluru", today + datetime.timedelta(days=3), "07:30", 90, 2000.0, 30),
                ("DG102", "Coimbatore", "Chennai", today + datetime.timedelta(days=2), "09:15", 65, 1800.0, 30),
                ("DG201", "Bengaluru", "Mumbai", today + datetime.timedelta(days=5), "13:00", 120, 3500.0, 40),
                ("DG301", "Chennai", "Hyderabad", today + datetime.timedelta(days=4), "17:45", 75, 2200.0, 30),
                ("DG401", "Coimbatore", "Kochi", today + datetime.timedelta(days=1), "06:00", 60, 1500.0, 20),
            ]
            for fn, s, d, ddate, dtime, dur, fare, seats in sample:
                c.execute(
                    "INSERT INTO flights (flight_no, src, dst, depart_date, depart_time, duration_minutes, base_fare, total_seats) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (fn, s, d, ddate.isoformat(), dtime, dur, fare, seats),
                )
            self.conn.commit()

    # User operations
    def create_user(self, username, password_hash):
        c = self.conn.cursor()
        try:
            c.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, password_hash, now_str()),
            )
            self.conn.commit()
            return c.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_user(self, username):
        c = self.conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        return c.fetchone()

    # Flight operations
    def search_flights(self, src=None, dst=None, depart_date=None):
        query = "SELECT * FROM flights WHERE 1=1"
        params = []
        if src:
            query += " AND LOWER(src) = LOWER(?)"
            params.append(src)
        if dst:
            query += " AND LOWER(dst) = LOWER(?)"
            params.append(dst)
        if depart_date:
            query += " AND depart_date = ?"
            params.append(depart_date)
        query += " ORDER BY depart_date, depart_time"
        c = self.conn.cursor()
        c.execute(query, tuple(params))
        return c.fetchall()

    def get_flight(self, flight_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM flights WHERE id = ?", (flight_id,))
        return c.fetchone()

    # Seat/booking related
    def seats_taken(self, flight_id):
        c = self.conn.cursor()
        c.execute("SELECT seat FROM bookings WHERE flight_id = ? AND status = 'BOOKED'", (flight_id,))
        return {row["seat"] for row in c.fetchall()}

    def create_booking(self, user_id, flight_id, seat, fare):
        c = self.conn.cursor()
        booking_ref = self._generate_booking_ref(user_id, flight_id)
        try:
            c.execute(
                "INSERT INTO bookings (booking_ref, user_id, flight_id, seat, fare, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (booking_ref, user_id, flight_id, seat, fare, "BOOKED", now_str()),
            )
            self.conn.commit()
            return booking_ref
        except sqlite3.IntegrityError:
            return None

    def _generate_booking_ref(self, user_id, flight_id):
        # Human-friendly booking reference
        rnd = random.randint(100, 999)
        return f"BK{user_id:03d}{flight_id:03d}{rnd}"

    def get_user_bookings(self, user_id):
        c = self.conn.cursor()
        c.execute(
            """SELECT b.*, f.flight_no, f.src, f.dst, f.depart_date, f.depart_time
               FROM bookings b
               JOIN flights f ON b.flight_id = f.id
               WHERE b.user_id = ? ORDER BY b.created_at DESC""",
            (user_id,),
        )
        return c.fetchall()

    def get_booking_by_ref(self, booking_ref, user_id=None):
        c = self.conn.cursor()
        if user_id:
            c.execute("SELECT * FROM bookings WHERE booking_ref = ? AND user_id = ?", (booking_ref, user_id))
        else:
            c.execute("SELECT * FROM bookings WHERE booking_ref = ?", (booking_ref,))
        return c.fetchone()

    def cancel_booking(self, booking_id):
        c = self.conn.cursor()
        c.execute("UPDATE bookings SET status = 'CANCELED' WHERE id = ? AND status = 'BOOKED'", (booking_id,))
        self.conn.commit()
        return c.rowcount > 0


# Business logic

class FlightBookingSystem:
    TAX_PERCENT = 0.05   # 5% tax
    SERVICE_FEE = 100.0  # flat service fee in currency units

    def __init__(self, db: DB):
        self.db = db
        self.current_user = None  # sqlite row of logged in user

    # User flows
    def register(self):
        clear_console()
        print("=== Register ===")
        while True:
            username = input("Choose a username: ").strip()
            if not username:
                print("Username cannot be empty.")
                continue
            if self.db.get_user(username):
                print("Username already exists. Choose another.")
                continue
            password = input_hidden("Choose a password: ")
            if len(password) < 4:
                print("Password too short (min 4 chars).")
                continue
            password2 = input_hidden("Confirm password: ")
            if password != password2:
                print("Passwords do not match.")
                continue
            uid = self.db.create_user(username, hash_password(password))
            if uid:
                print("Registration successful! Please login.")
                return
            else:
                print("Registration failed. Try again.")
                return

    def login(self):
        clear_console()
        print("=== Login ===")
        username = input("Username: ").strip()
        password = input_hidden("Password: ")
        user = self.db.get_user(username)
        if not user:
            print("User not found.")
            return False
        if user["password_hash"] != hash_password(password):
            print("Incorrect password.")
            return False
        self.current_user = user
        print(f"Welcome, {user['username']}!")
        return True

    def logout(self):
        self.current_user = None
        print("Logged out.")

    # Flight search & booking
    def search_and_display(self):
        clear_console()
        print("=== Search Flights ===")
        src = input("Source (leave blank to skip): ").strip() or None
        dst = input("Destination (leave blank to skip): ").strip() or None
        ddate = input("Departure date (YYYY-MM-DD, leave blank to skip): ").strip() or None
        if ddate:
            try:
                datetime.date.fromisoformat(ddate)
            except Exception:
                print("Invalid date format. Use YYYY-MM-DD.")
                return []
        flights = self.db.search_flights(src, dst, ddate)
        if not flights:
            print("No flights found.")
            return []
        print("\nFound flights:")
        for f in flights:
            print(self._format_flight_row(f))
        return flights

    def _format_flight_row(self, f):
        return (
            f"[ID:{f['id']}] {f['flight_no']} | {f['src']} -> {f['dst']} | Date: {f['depart_date']} {f['depart_time']} | "
            f"Duration: {f['duration_minutes']}m | Base fare: {f['base_fare']:.2f} | Seats: {f['total_seats']}"
        )

    def show_seat_map(self, flight):
        # For simplicity, create rows of 6 seats (A-F). seat numbering from 1..N
        total = flight["total_seats"]
        seats_per_row = 6
        rows = (total + seats_per_row - 1) // seats_per_row
        taken = self.db.seats_taken(flight["id"])
        print("\nSeat Map (X = taken) :\n")
        for r in range(1, rows + 1):
            row_seats = []
            for s in range(1, seats_per_row + 1):
                seat_num = (r - 1) * seats_per_row + s
                if seat_num > total:
                    break
                seat_label = f"{seat_num}{chr(ord('A') + s - 1)}"
                if seat_label in taken:
                    row_seats.append(f"[X]")
                else:
                    row_seats.append(f"[{seat_label}]")
            print(" ".join(row_seats))
        print()

    def calculate_fare(self, base_fare):
        tax = base_fare * self.TAX_PERCENT
        total = base_fare + tax + self.SERVICE_FEE
        return round(total, 2), round(tax, 2), round(self.SERVICE_FEE, 2)

    def book_flight(self):
        if not self.current_user:
            print("Please login to book.")
            return
        flights = self.search_and_display()
        if not flights:
            return
        try:
            fid = int(input("\nEnter Flight ID to book: ").strip())
        except ValueError:
            print("Invalid Flight ID.")
            return
        flight = self.db.get_flight(fid)
        if not flight:
            print("Flight not found.")
            return
        self.show_seat_map(flight)
        seat = input("Choose seat label exactly as displayed (e.g., 1A): ").strip().upper()
        if not seat:
            print("No seat selected.")
            return
        # Validate seat label exists
        try:
            seat_num_part = int(''.join(ch for ch in seat if ch.isdigit()))
            seats_per_row = 6
            max_seat_num = flight["total_seats"]
            if seat_num_part < 1 or seat_num_part > max_seat_num:
                print("Seat number out of range.")
                return
        except Exception:
            print("Invalid seat format.")
            return
        if seat in self.db.seats_taken(flight["id"]):
            print("Seat already taken. Choose another.")
            return
        # Fare calculation
        base = flight["base_fare"]
        total, tax, service = self.calculate_fare(base)
        print(f"\nFare breakdown:\n Base fare: {base:.2f}\n Tax (5%): {tax:.2f}\n Service fee: {service:.2f}\n Total: {total:.2f}")
        confirm = input("Confirm booking? (y/n): ").strip().lower()
        if confirm != "y":
            print("Booking cancelled by user.")
            return
        booking_ref = self.db.create_booking(self.current_user["id"], flight["id"], seat, total)
        if booking_ref:
            print(f"\nBooking successful! Reference: {booking_ref}")
            print(f"Seat: {seat} | Total Paid: {total:.2f}")
        else:
            print("Failed to create booking. Try again.")

    # Booking management
    def view_bookings(self):
        if not self.current_user:
            print("Please login to view bookings.")
            return
        bookings = self.db.get_user_bookings(self.current_user["id"])
        if not bookings:
            print("No bookings found.")
            return
        print("\nYour Bookings:")
        for b in bookings:
            status = b["status"]
            print(
                textwrap.dedent(
                    f"""
                    Ref: {b['booking_ref']} | Flight: {b['flight_no']} ({b['src']} -> {b['dst']})
                    Date/Time: {b['depart_date']} {b['depart_time']} | Seat: {b['seat']} | Fare: {b['fare']:.2f} | Status: {status} | Booked At: {b['created_at']}
                    """
                ).strip()
            )
            print("-" * 70)

    def cancel_booking_flow(self):
        if not self.current_user:
            print("Please login to cancel bookings.")
            return
        self.view_bookings()
        ref = input("\nEnter booking reference to cancel (or blank to go back): ").strip()
        if not ref:
            return
        b = self.db.get_booking_by_ref(ref, self.current_user["id"])
        if not b:
            print("Booking not found.")
            return
        if b["status"] == "CANCELED":
            print("Booking already canceled.")
            return
        confirm = input(f"Are you sure you want to cancel {ref}? (y/n): ").strip().lower()
        if confirm != "y":
            print("Cancellation aborted.")
            return
        ok = self.db.cancel_booking(b["id"])
        if ok:
            refund = self._calculate_refund(b["fare"], b["created_at"])
            print(f"Booking {ref} canceled. Estimated refund: {refund:.2f}")
        else:
            print("Failed to cancel booking.")

    def _calculate_refund(self, fare_paid, created_at_str):
        # Simple policy: full refund if canceled >48 hours before now; else 50% refund
        try:
            created_at = datetime.datetime.fromisoformat(created_at_str)
        except Exception:
            created_at = datetime.datetime.now()
        delta = datetime.datetime.now() - created_at
        if delta.total_seconds() > 48 * 3600:
            return round(fare_paid, 2)
        else:
            return round(fare_paid * 0.5, 2)


# CLI Menu

def main_menu(app: FlightBookingSystem):
    while True:
        clear_console()
        print("=== Flight Ticket Booking System ===")
        if app.current_user:
            print(f"Logged in as: {app.current_user['username']}")
        else:
            print("Not logged in.")
        print(
            """
1. Register
2. Login
3. Search Flights
4. Book Flight
5. View My Bookings
6. Cancel Booking
7. Logout
0. Exit
"""
        )
        choice = input("Choose an option: ").strip()
        if choice == "1":
            app.register()
            input("\nPress Enter to continue...")
        elif choice == "2":
            if app.login():
                input("\nPress Enter to continue...")
            else:
                input("\nLogin failed. Press Enter to continue...")
        elif choice == "3":
            app.search_and_display()
            input("\nPress Enter to continue...")
        elif choice == "4":
            app.book_flight()
            input("\nPress Enter to continue...")
        elif choice == "5":
            app.view_bookings()
            input("\nPress Enter to continue...")
        elif choice == "6":
            app.cancel_booking_flow()
            input("\nPress Enter to continue...")
        elif choice == "7":
            app.logout()
            input("\nPress Enter to continue...")
        elif choice == "0":
            print("Goodbye!")
            sys.exit(0)
        else:
            print("Invalid option.")
            input("\nPress Enter to continue...")


# Entry point

if __name__ == "__main__":
    db = DB()
    app = FlightBookingSystem(db)
    try:
        main_menu(app)
    except KeyboardInterrupt:
        print("\nExiting. Goodbye!")
        sys.exit(0)
