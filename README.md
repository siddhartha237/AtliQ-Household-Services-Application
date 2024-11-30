# **AtliQ Household Services Application**  

## **Overview**  
The AtliQ Household Services Application is a comprehensive platform designed to simplify and enhance the process of connecting customers with professional home service providers. It streamlines service requests, bookings, and management while ensuring ease of use for all stakeholders: Admin, Service Professionals, and Customers.  

## **Features**  
- **Admin Role**:  
  - Manage platform operations, including user approvals and service monitoring.  
  - View and update professional profiles and block users if necessary.  
- **Service Professionals Role**:  
  - Accept or reject customer requests and manage service statuses.  
  - Maintain service profiles with ratings and reviews for performance tracking.  
- **Customer Role**:  
  - Book and track services, provide feedback, and view professional details.  

## **Tech Stack**  
### **Backend**  
- **Flask (3.0.3)**: Lightweight web framework for routing and request handling.  
- **Flask-SQLAlchemy (3.1.1)**: ORM integration for database operations with SQLite.  

### **Frontend**  
- **Jinja2 (3.1.4)**: Templating engine for dynamic HTML generation.  
- **Bootstrap**: Responsive design framework for modern UI/UX.  

### **Database**  
- **SQLite**: Lightweight, serverless database for efficient data management.  

### **Data Visualization**  
- **Matplotlib (3.9.2)** and **Seaborn (0.13.2)**: Libraries for creating visual insights into platform usage and trends.  

## **Setup Instructions**  
1. Clone the repository:  
   ```bash  
   git clone https://github.com/your-repo-url/atliq-household-services.git  
   cd atliq-household-services  
   ```  
2. Create a virtual environment and activate it:  
   ```bash  
   python -m venv venv  
   source venv/bin/activate  # On Windows: venv\Scripts\activate  
   ```  
3. Install the required dependencies:  
   ```bash  
   pip install -r requirements.txt  
   ```  
4. Initialize the database:  
   ```bash  
   flask db init  
   flask db migrate  
   flask db upgrade  
   ```  
5. Run the application:  
   ```bash  
   flask run  
   ```  
6. Access the application in your browser at `http://127.0.0.1:5000`.  

## **Project Highlights**  
- Designed database schemas with normalized tables for efficient data storage and retrieval.  
- Implemented secure authentication and authorization for different user roles.  
- Developed dashboards with visual analytics for insights into service trends and user activity.  

## **Screenshots**  
<img width="935" alt="image" src="https://github.com/user-attachments/assets/bf4f7273-8a30-4138-9504-f888ce1522dc">

<img width="949" alt="image" src="https://github.com/user-attachments/assets/40ca0c59-db17-410d-9eb8-4862ae0e4b14">

<img width="950" alt="image" src="https://github.com/user-attachments/assets/d1932cf7-36a4-4146-9fc4-011b927b0a45">

<img width="944" alt="image" src="https://github.com/user-attachments/assets/80b73acd-3e3e-4139-8bac-ca6408058280">

<img width="954" alt="image" src="https://github.com/user-attachments/assets/cd4b4193-3442-4056-b907-5b0658bd4d7e">

<img width="955" alt="image" src="https://github.com/user-attachments/assets/1706c15a-ec63-47d1-acdf-6613cc4dd0d6">

<img width="958" alt="image" src="https://github.com/user-attachments/assets/5604c818-4e59-44d4-be27-8be9bb3857b3">

<img width="953" alt="image" src="https://github.com/user-attachments/assets/ac54a1a6-f201-4ee9-ac18-4927c2932171">

<img width="959" alt="image" src="https://github.com/user-attachments/assets/531b3a83-6482-4bcb-9893-836df8d1bc0a">

<img width="956" alt="image" src="https://github.com/user-attachments/assets/77cc7476-d018-4c64-bfe5-b859b0741b63">

<img width="959" alt="image" src="https://github.com/user-attachments/assets/1aea2c75-f119-4736-90fd-8e7eba969b81">

## **Future Enhancements**  
- Add real-time notifications for service updates.  
- Enable multi-language support for broader accessibility.  
- Integrate advanced analytics for predictive insights.  

## **Contact Information**  
**Developer**: Siddhartha Singh  
**Email**: 22f3002435@ds.study.iitm.ac.in  
