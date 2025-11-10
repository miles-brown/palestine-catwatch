_


# Palestine Catwatch Directory

The Palestine Catwatch Directory is a web application designed to catalog and track law enforcement personnel at public events. It provides a searchable database of officers, their affiliations, and their presence at various demonstrations and public gatherings. The primary goal of this project is to provide a resource for activists, observers, and the general public to identify and monitor police activity in a transparent and accessible manner.

This project is built with a clean, user-friendly interface that prioritizes efficient information retrieval and cross-referencing. The design is minimalist and functional, resembling a database or wiki to ensure that the focus remains on the data itself.




## Core Features

*   **Searchable Directory:** The homepage features a simple and intuitive search interface. Users can look up officers by their **Collar Number** (badge/shoulder number) or by their **Breed** (police force/constabulary).
*   **Event Filtering:** A sidebar or dropdown menu allows users to filter the directory by specific **Events** (protests/demonstrations), making it easy to see which officers were present at a particular gathering.
*   **Individual “Cat” Profile Pages:** Each officer has a detailed profile page that includes:
    *   **Photo:** A clear image of the officer’s face.
    *   **Collar Number:** Their official identification number.
    *   **Breed/Pride:** Their affiliated police force (e.g., Metropolitan Police, South Yorkshire Police).
    *   **Description:** A neutral, factual description of the officer’s appearance, role (e.g., Liaison Officer, Territorial Support Group), and equipment.
*   **Event History:** Each profile includes a chronological list of events where the officer has been documented. This “Where This Cat Has Been Spotted” section includes:
    *   The date of the event.
    *   The location and name of the event/protest.
    *   A brief, factual log of witnessed activities or interactions (e.g., “Present at kettle on Main St,” “Documented conducting stop-and-search”).
*   **Source Links:** To maintain a commitment to factual reporting, each event entry includes fields to link to external source material, such as video timestamps or photo galleries from the event.
*   **Events Directory Page:** A comprehensive list of all documented protests and events. Each event links to a page showing all “cats” (officers) who were documented at that specific event.




## Design Aesthetic

The design of the Palestine Catwatch Directory is minimalist and functional, with a focus on usability and clarity. The aesthetic is similar to a database or a wiki, ensuring that the information is presented in a straightforward and easy-to-navigate format. The use of “cat” terminology is a stylistic choice for the internal organization of data and is not intended to be inflammatory.

## Disclaimer

This website acts as a public archive of documented, publicly-observable information. All information is sourced from public events and publicly available materials. This directory is presented for informational purposes only.




## Deployment

To deploy this application, you can use a production-ready WSGI server like Gunicorn. Here are the general steps:

1.  **Install Gunicorn:**

    ```bash
    pip install gunicorn
    ```

2.  **Run the application with Gunicorn:**

    ```bash
    gunicorn -w 4 -b 0.0.0.0:5000 src.main:app
    ```

    This command will start the application with 4 worker processes on port 5000.

3.  **Set up a reverse proxy (optional but recommended):**

    For a production environment, it's recommended to use a reverse proxy like Nginx to handle incoming requests and forward them to Gunicorn. This can improve performance and security.



## Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/miles-brown/palestine-catwatch.git
    cd palestine-catwatch
    ```

2.  **Create a virtual environment:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application:**

    ```bash
    python src/main.py
    ```

    The application will be available at `http://localhost:5000`.

## Usage

### Adding Officers

1.  Navigate to the "Add Cat" page from the main navigation.
2.  Fill in the required fields:
    *   **Collar Number:** The officer's badge or shoulder number (required).
    *   **Breed:** The police force or constabulary (required).
    *   **Photo URL:** A link to the officer's photograph (optional).
    *   **Role:** The officer's role or position (optional).
    *   **Description:** A neutral, factual description of the officer (optional).
    *   **Equipment:** Details about the officer's equipment (optional).
3.  Click "Add Cat" to save the officer to the database.

### Adding Events

1.  Navigate to the "Add Event" page from the main navigation.
2.  Fill in the required fields:
    *   **Event Name:** The name of the protest or demonstration (required).
    *   **Date:** The date of the event (required).
    *   **Location:** The location where the event took place (required).
    *   **Description:** Additional details about the event (optional).
3.  Click "Add Event" to save the event to the database.

### Searching for Officers

*   **By Collar Number:** Enter the officer's badge or shoulder number in the "Search by Collar Number" field and click "Search."
*   **By Breed:** Enter the name of the police force in the "Search by Breed (Force)" field and click "Search."
*   **By Event:** Use the "Filter by Event" dropdown to see all officers documented at a specific event.

### Viewing Officer Profiles

Click on any officer in the search results to view their detailed profile, including their event history and documented activities.

### Viewing Events

Navigate to the "Events" page to see a list of all documented events. Click on an event to see all officers who were present at that event.

## Technical Details

### Backend

The backend is built with Flask and uses SQLAlchemy for database management. The main components include:

*   **Models:** `Officer`, `Event`, and `EventOfficer` models define the database schema.
*   **Routes:** API endpoints for CRUD operations on officers, events, and their relationships.
*   **Database:** SQLite database for development (can be easily switched to PostgreSQL or MySQL for production).

### Frontend

The frontend is built with vanilla HTML, CSS, and JavaScript. It features:

*   **Responsive Design:** The interface works on both desktop and mobile devices.
*   **Single Page Application:** Navigation between pages is handled with JavaScript without full page reloads.
*   **Clean UI:** Minimalist design focused on functionality and usability.

### API Endpoints

*   `GET /api/officers` - Get all officers
*   `GET /api/officers/<id>` - Get a specific officer with event history
*   `POST /api/officers` - Create a new officer
*   `PUT /api/officers/<id>` - Update an officer
*   `DELETE /api/officers/<id>` - Delete an officer
*   `GET /api/search/collar/<collar_number>` - Search by collar number
*   `GET /api/search/breed/<breed>` - Search by police force
*   `GET /api/events` - Get all events
*   `GET /api/events/<id>` - Get a specific event with officers present
*   `POST /api/events` - Create a new event
*   `POST /api/event-officers` - Link an officer to an event

## Contributing

Contributions are welcome! Please follow these guidelines:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes and test them thoroughly.
4.  Submit a pull request with a clear description of your changes.

## License

This project is provided as-is for informational and educational purposes. Please ensure compliance with local laws and regulations when using this software.

