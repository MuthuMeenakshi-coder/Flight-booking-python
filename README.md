# Flight Ticket Booking System (CLI)

A **Command-Line Interface (CLI)** based Flight Ticket Booking System built in Python with persistent data storage using **SQLite**. This system allows users to register, search flights, book seats, view bookings, and cancel reservations.

---

## 🚀 Features

- **User Management**
  - Register new users with password hashing
  - Login / Logout functionality

- **Flight Management**
  - Search flights by source, destination, and date
  - View flight details including departure time, duration, base fare, and available seats

- **Booking Management**
  - Select seat from a visual seat map
  - Fare calculation with base fare, taxes, and service fees
  - View booking history
  - Cancel bookings with a simple refund policy

- **Database**
  - Persistent storage using SQLite
  - Automatic seeding of sample flights for testing

- **User-friendly CLI**
  - Clear menus and prompts
  - Input validation and error handling

---

## 🛠️ Technologies & Libraries Used

- **Python 3**
- **SQLite** for database storage
- **hashlib** for password hashing
- **getpass** for secure password input
- **datetime** for date and time handling
- **random** for generating booking references

---

## 💻 How to Run

1. Clone the repository:


git clone https://github.com/MuthuMeenakshi-coder/Flight-booking-python.git
cd Flight-booking-python

2.Run the main script:

python flight_booking.py

3.Follow the CLI prompts to:

Register a new user or login

Search and book flights

View or cancel bookings
