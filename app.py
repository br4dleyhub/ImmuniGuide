from flask import Flask, render_template, request
import sqlite3
import os
import requests


app = Flask(__name__)


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

DATABASE = os.path.join(
    os.path.dirname(__file__),
    "immunisation-2.db"
)


# =========================================================
# WHO API
# =========================================================

WHO_API = "https://www.who.int/api/news/newsitems"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


# =========================================================
# WHO NEWS
# =========================================================

def get_news():

    try:

        response = requests.get(
            WHO_API,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        articles = []


        # WHO API may return the articles
        # inside a "value" object.

        if isinstance(data, dict):

            data = data.get(
                "value",
                []
            )


        # Keep the latest 10 articles.

        for item in data[:10]:

            title = item.get(
                "Title",
                "No title"
            )


            link = item.get(
                "ItemDefaultUrl",
                "#"
            )


            # Convert relative WHO links
            # into complete URLs.

            if link.startswith("/"):

                link = "https://www.who.int" + link


            published = item.get(
                "FormatedDate",
                ""
            )


            news_type = item.get(
                "NewsType",
                "WHO NEWS"
            )


            # -------------------------------------------------
            # Determine article category
            # -------------------------------------------------

            title_lower = title.lower()


            if any(word in title_lower for word in [

                "ebola",
                "measles",
                "polio",
                "outbreak",
                "disease",
                "mpox",
                "cholera",
                "infection"

            ]):

                category = "OUTBREAK"


            elif any(word in title_lower for word in [

                "trial",
                "research",
                "development",
                "candidate",
                "mrna",
                "clinical"

            ]):

                category = "VACCINE DEVELOPMENT"


            elif any(word in title_lower for word in [

                "vaccine",
                "vaccination",
                "immunisation",
                "immunization",
                "coverage",
                "vaccinated"

            ]):

                category = "IMMUNISATION"


            elif any(word in title_lower for word in [

                "guidance",
                "recommendation",
                "position paper",
                "policy",
                "guideline"

            ]):

                category = "POLICY"


            else:

                category = "HEALTH NEWS"


            articles.append({

                "title": title,

                "link": link,

                "published": published,

                "category": category,

                "news_type": news_type

            })


        return articles


    except Exception as error:

        print(
            "News API error:",
            error
        )

        return []


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "home.html"
    )


# =========================================================
# EXPLORE
# =========================================================

@app.route("/explore")
def explore():

    country = request.args.get(
        "country"
    )

    year = request.args.get(
        "year"
    )

    antigen = request.args.get(
        "antigen"
    )


    connection = get_db_connection()


    # ---------------------------------------------------------
    # Get selected vaccination result
    # ---------------------------------------------------------

    result = connection.execute(
        """
        SELECT
            Vaccination.*,
            Antigen.name AS vaccine_name,
            Country.name AS country_name
        FROM Vaccination
        JOIN Antigen
            ON Vaccination.antigen = Antigen.AntigenID
        JOIN Country
            ON Vaccination.country = Country.CountryID
        WHERE Vaccination.country = ?
          AND Vaccination.year = ?
          AND Vaccination.antigen = ?
        """,
        (
            country,
            year,
            antigen
        )
    ).fetchone()


    coverage_level = None

    people_per_100 = None

    target_population = None

    doses_administered = None


    # ---------------------------------------------------------
    # Process selected result
    # ---------------------------------------------------------

    if result:

        coverage_value = result["coverage"]


        # -----------------------------------------------------
        # Safely convert coverage
        # -----------------------------------------------------

        try:

            if (
                coverage_value is not None
                and str(coverage_value).strip() != ""
            ):

                coverage = float(
                    coverage_value
                )

            else:

                coverage = None


        except (ValueError, TypeError):

            coverage = None


        # -----------------------------------------------------
        # Target population
        # -----------------------------------------------------

        try:

            target_population = round(
                float(result["target_num"])
            )

        except (ValueError, TypeError):

            target_population = None


        # -----------------------------------------------------
        # Doses administered
        # -----------------------------------------------------

        try:

            doses_administered = round(
                float(result["doses"])
            )

        except (ValueError, TypeError):

            doses_administered = None


        # -----------------------------------------------------
        # Coverage level
        # -----------------------------------------------------

        if coverage is not None:

            if coverage >= 90:

                coverage_level = "Very High Coverage"


            elif coverage >= 75:

                coverage_level = "High Coverage"


            elif coverage >= 50:

                coverage_level = "Moderate Coverage"


            else:

                coverage_level = "Low Coverage"


            people_per_100 = round(
                coverage
            )


    # ---------------------------------------------------------
    # Get countries
    # ---------------------------------------------------------

    countries = connection.execute(
        """
        SELECT CountryID, name
        FROM Country
        ORDER BY name
        """
    ).fetchall()


    # ---------------------------------------------------------
    # Get years
    # ---------------------------------------------------------

    years = connection.execute(
        """
        SELECT YearID
        FROM YearDate
        ORDER BY YearID DESC
        """
    ).fetchall()


    # ---------------------------------------------------------
    # Get vaccines
    # ---------------------------------------------------------

    antigens = connection.execute(
        """
        SELECT AntigenID, name
        FROM Antigen
        ORDER BY name
        """
    ).fetchall()


    connection.close()


    return render_template(

        "explore.html",

        countries=countries,

        years=years,

        antigens=antigens,

        result=result,

        coverage_level=coverage_level,

        people_per_100=people_per_100,

        target_population=target_population,

        doses_administered=doses_administered

    )


# =========================================================
# COMPARE
# =========================================================

@app.route("/compare")
def compare():

    country = request.args.get(
        "country"
    )

    antigen = request.args.get(
        "antigen"
    )

    year1 = request.args.get(
        "year1"
    )

    year2 = request.args.get(
        "year2"
    )


    connection = get_db_connection()


    # ---------------------------------------------------------
    # Get countries
    # ---------------------------------------------------------

    countries = connection.execute(
        """
        SELECT CountryID, name
        FROM Country
        ORDER BY name
        """
    ).fetchall()


    # ---------------------------------------------------------
    # Get vaccines
    # ---------------------------------------------------------

    antigens = connection.execute(
        """
        SELECT AntigenID, name
        FROM Antigen
        ORDER BY name
        """
    ).fetchall()


    # ---------------------------------------------------------
    # Get years
    # ---------------------------------------------------------

    years = connection.execute(
        """
        SELECT YearID
        FROM YearDate
        ORDER BY YearID DESC
        """
    ).fetchall()


    result1 = None

    result2 = None

    coverage_change = None

    comparison_message = None

    comparison_status = None


    # ---------------------------------------------------------
    # Get both years
    # ---------------------------------------------------------

    if country and antigen and year1 and year2:

        result1 = connection.execute(
            """
            SELECT *
            FROM Vaccination
            WHERE country = ?
              AND antigen = ?
              AND year = ?
            """,
            (
                country,
                antigen,
                year1
            )
        ).fetchone()


        result2 = connection.execute(
            """
            SELECT *
            FROM Vaccination
            WHERE country = ?
              AND antigen = ?
              AND year = ?
            """,
            (
                country,
                antigen,
                year2
            )
        ).fetchone()


    # ---------------------------------------------------------
    # Calculate coverage change
    # ---------------------------------------------------------

    if result1 and result2:

        try:

            coverage1_value = result1["coverage"]

            coverage2_value = result2["coverage"]


            if (
                coverage1_value is not None
                and str(coverage1_value).strip() != ""
                and coverage2_value is not None
                and str(coverage2_value).strip() != ""
            ):

                coverage1 = float(
                    coverage1_value
                )

                coverage2 = float(
                    coverage2_value
                )


                coverage_change = round(
                    coverage2 - coverage1,
                    2
                )


        except (ValueError, TypeError):

            coverage_change = None


    # ---------------------------------------------------------
    # Create comparison message
    # ---------------------------------------------------------

    if coverage_change is not None:

        if coverage_change > 0:

            comparison_message = (

                f"Coverage was "
                f"{abs(coverage_change)} "
                f"percentage points higher in "
                f"{year2} than in {year1}."

            )


            comparison_status = (
                "Coverage increased"
            )


        elif coverage_change < 0:

            comparison_message = (

                f"Coverage was "
                f"{abs(coverage_change)} "
                f"percentage points lower in "
                f"{year2} than in {year1}."

            )


            comparison_status = (
                "Coverage decreased"
            )


        else:

            comparison_message = (

                f"Coverage was the same in "
                f"{year1} and {year2}."

            )


            comparison_status = (
                "No change in coverage"
            )


    connection.close()


    return render_template(

        "compare.html",

        countries=countries,

        antigens=antigens,

        years=years,

        year1=year1,

        year2=year2,

        result1=result1,

        result2=result2,

        coverage_change=coverage_change,

        comparison_message=comparison_message,

        comparison_status=comparison_status

    )


# =========================================================
# TRENDS
# =========================================================

@app.route("/trends")
def trends():

    country = request.args.get(
        "country"
    )

    antigen = request.args.get(
        "antigen"
    )


    connection = get_db_connection()


    # ---------------------------------------------------------
    # Get countries
    # ---------------------------------------------------------

    countries = connection.execute(
        """
        SELECT CountryID, name
        FROM Country
        ORDER BY name
        """
    ).fetchall()


    # ---------------------------------------------------------
    # Get vaccines
    # ---------------------------------------------------------

    antigens = connection.execute(
        """
        SELECT AntigenID, name
        FROM Antigen
        ORDER BY name
        """
    ).fetchall()


    trend_data = None

    first_coverage = None

    latest_coverage = None

    coverage_change = None

    highest = None

    lowest = None


    # ---------------------------------------------------------
    # Get trend data
    # ---------------------------------------------------------

    if country and antigen:

        rows = connection.execute(
            """
            SELECT
                year,
                coverage
            FROM Vaccination
            WHERE country = ?
              AND antigen = ?
            ORDER BY year
            """,
            (
                country,
                antigen
            )
        ).fetchall()


        trend_data = []


        for row in rows:

            coverage = row["coverage"]


            # -------------------------------------------------
            # Handle empty / invalid coverage values
            # -------------------------------------------------

            try:

                if (
                    coverage is None
                    or str(coverage).strip() == ""
                ):

                    continue


                numeric_coverage = float(
                    coverage
                )


            except (ValueError, TypeError):

                continue


            # -------------------------------------------------
            # Add valid data
            # -------------------------------------------------

            trend_data.append({

                "year": row["year"],

                "coverage": numeric_coverage,

                "width": numeric_coverage

            })


        # -----------------------------------------------------
        # Calculate summary statistics
        # -----------------------------------------------------

        if trend_data:

            first_coverage = (
                trend_data[0]["coverage"]
            )


            latest_coverage = (
                trend_data[-1]["coverage"]
            )


            coverage_change = round(

                latest_coverage
                - first_coverage,

                2

            )


            highest = max(

                trend_data,

                key=lambda x: x["coverage"]

            )


            lowest = min(

                trend_data,

                key=lambda x: x["coverage"]

            )


    connection.close()


    return render_template(

        "trends.html",

        countries=countries,

        antigens=antigens,

        trend_data=trend_data,

        first_coverage=first_coverage,

        latest_coverage=latest_coverage,

        coverage_change=coverage_change,

        highest=highest,

        lowest=lowest

    )


# =========================================================
# INSIGHTS
# =========================================================

@app.route("/insights")
def insights():

    articles = get_news()


    return render_template(

        "insights.html",

        articles=articles

    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=False
    )