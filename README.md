# A/B Testing Platform

Production-grade A/B testing platform with advanced statistical methods, built for demonstrating experimentation expertise.

## Statistical Methods
- **CUPED** - Variance reduction using pre-experiment data
- **Sequential Testing** - Early stopping with O'Brien-Fleming boundaries
- **Bayesian A/B Testing** - Probability statements for stakeholders
- **Multiple Testing Correction** - Bonferroni & Benjamini-Hochberg

## Tech Stack
- **Backend**: FastAPI, PostgreSQL, SQLAlchemy, SciPy
- **Frontend**: React, Vite, Tailwind CSS, Recharts
- **Infrastructure**: Docker, AWS (EC2, RDS, S3), GitHub Actions

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Node.js 18+ (for frontend, Week 4)

### Setup
```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/ab-testing-platform.git
cd ab_testing_platform

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Run the API
uvicorn app.main:app --reload
```

### Verify
Visit http://localhost:8000/health — you should see:
```json
{"status": "healthy", "app": "A/B Testing Platform", "version": "0.1.0"}
```

