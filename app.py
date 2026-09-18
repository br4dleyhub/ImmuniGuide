from flask import Flask, render_template, request
import sqlite3
import os
import requests
from datetime import datetime


app = Flask(__name__)


print("====================================================")
print("THIS IS MY APP.PY")
print("APP FILE:", __file__)
print("====================================================")


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
            timeout=45
        )

        response.raise_for_status()

        data = response.json()

        articles = []

        if isinstance(data, dict):

            data = data.get(
                "value",
                []
            )

        if not isinstance(data, list):

            data = []


        # =====================================================
        # SORT BY PUBLICATION DATE
        # =====================================================

        def get_date(item):

            date = item.get(
                "PublicationDateAndTime",
                ""
            )

            if date:

                try:

                    return datetime.fromisoformat(
                        date.replace(
                            "Z",
                            "+00:00"
                        )
                    )

                except (ValueError, TypeError):

                    pass


            date = item.get(
                "FormatedDate",
                ""
            )

            try:

                return datetime.strptime(
                    date,
                    "%d %B %Y"
                )

            except (ValueError, TypeError):

                return datetime.min


        data.sort(
            key=get_date,
            reverse=True
        )


        # =====================================================
        # GET THE 10 NEWEST ARTICLES
        # =====================================================

        for item in data[:10]:

            title = item.get(
                "Title",
                "WHO News"
            )


            # =================================================
            # ARTICLE LINK
            # =================================================

            link = item.get(
                "ItemDefaultUrl",
                ""
            )


            if link:

                link = link.replace(
                    "https://www.who.int",
                    ""
                )


                if not link.startswith("/"):

                    link = "/" + link


                if not link.startswith(
                    "/news/item/"
                ):

                    link = (
                        "/news/item"
                        + link
                    )


                link = (
                    "https://www.who.int"
                    + link
                )


            if not link:

                continue


            # =================================================
            # PUBLICATION DATE
            # =================================================

            published = item.get(
                "FormatedDate",
                ""
            )


            # =================================================
            # NEWS TYPE
            # =================================================

            news_type = item.get(
                "NewsType",
                "WHO NEWS"
            )


            # =================================================
            # SIMPLE CATEGORY
            # =================================================

            title_lower = title.lower()


            if any(
                word in title_lower
                for word in [
                    "ebola",
                    "measles",
                    "polio",
                    "outbreak",
                    "mpox",
                    "cholera",
                    "infection",
                    "disease"
                ]
            ):

                category = "OUTBREAK & DISEASE"


            elif any(
                word in title_lower
                for word in [
                    "vaccine",
                    "vaccination",
                    "immunisation",
                    "immunization",
                    "vaccinated",
                    "coverage"
                ]
            ):

                category = "IMMUNISATION"


            elif any(
                word in title_lower
                for word in [
                    "trial",
                    "research",
                    "development",
                    "candidate",
                    "mrna",
                    "clinical"
                ]
            ):

                category = "VACCINE DEVELOPMENT"


            elif any(
                word in title_lower
                for word in [
                    "guidance",
                    "recommendation",
                    "position paper",
                    "policy",
                    "guideline"
                ]
            ):

                category = "POLICY & GUIDANCE"


            else:

                category = "GLOBAL HEALTH"


            # =================================================
            # SAVE ARTICLE
            # =================================================

            articles.append({

                "title": title,

                "link": link,

                "published": published,

                "category": category,

                "news_type": news_type

            })


        print(
            "WHO NEWS ARTICLES LOADED:",
            len(articles)
        )


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

    conn = get_db_connection()


    mission = conn.execute("""
        SELECT title, content
        FROM AboutInfo
        WHERE info_type = 'mission'
        LIMIT 1
    """).fetchone()


    personas = conn.execute("""
        SELECT title, content
        FROM AboutInfo
        WHERE info_type = 'persona'
    """).fetchall()


    team = conn.execute("""
        SELECT title, content
        FROM AboutInfo
        WHERE info_type = 'team'
    """).fetchall()


    facts = conn.execute("""
        SELECT title, content
        FROM AboutInfo
        WHERE info_type = 'fact'
    """).fetchall()


    teamwork = conn.execute("""
        SELECT title, content
        FROM AboutInfo
        WHERE info_type = 'teamwork'
        LIMIT 1
    """).fetchone()


    countries = conn.execute("""
        SELECT COUNT(*)
        FROM Country
    """).fetchone()[0]


    years = conn.execute("""
        SELECT COUNT(DISTINCT YearID)
        FROM YearDate
    """).fetchone()[0]


    antigens = conn.execute("""
        SELECT COUNT(*)
        FROM Antigen
    """).fetchone()[0]


    infection_types = conn.execute("""
        SELECT COUNT(*)
        FROM Infection_Type
    """).fetchone()[0]


    conn.close()


    return render_template(
        "home.html",

        mission=mission,

        personas=personas,

        team=team,

        facts=facts,

        teamwork=teamwork,

        countries=countries,

        years=years,

        antigens=antigens,

        infection_types=infection_types
    )


# =========================================================
# EXPLORE
# =========================================================

@app.route("/explore")
def explore():

    conn = get_db_connection()


    # =========================================================
    # GET FILTERS
    # =========================================================

    region = request.args.get(
        "region",
        ""
    ).strip()

    country = request.args.get(
        "country",
        ""
    ).strip()

    year = request.args.get(
        "year",
        ""
    ).strip()

    antigen = request.args.get(
        "antigen",
        ""
    ).strip()


    # =========================================================
    # DEFAULT VALUES
    # =========================================================

    result = None

    coverage_level = None

    people_per_100 = None

    target_population = None

    doses_administered = None

    regional_summary = None

    regional_coverage_level = None

    herd_immunity_status = None

    countries_90 = []

    countries_90_percentage = None


    # =========================================================
    # REGIONS
    # =========================================================

    regions = conn.execute("""
        SELECT
            RegionID,
            region
        FROM Region
        ORDER BY region
    """).fetchall()


    # =========================================================
    # COUNTRIES
    # =========================================================

    if region:

        countries = conn.execute("""
            SELECT
                CountryID,
                name,
                region,
                economy
            FROM Country
            WHERE region = ?
            ORDER BY name
        """, (
            region,
        )).fetchall()

    else:

        countries = conn.execute("""
            SELECT
                CountryID,
                name,
                region,
                economy
            FROM Country
            ORDER BY name
        """).fetchall()


    # =========================================================
    # YEARS
    # =========================================================

    years = conn.execute("""
        SELECT YearID
        FROM YearDate
        ORDER BY YearID DESC
    """).fetchall()


    # =========================================================
    # ANTIGENS
    # =========================================================

    antigens = conn.execute("""
        SELECT
            AntigenID,
            name
        FROM Antigen
        ORDER BY name
    """).fetchall()


    # =========================================================
    # COUNTRY RESULT
    # =========================================================

    if country and year and antigen:

        query = """
            SELECT
                Vaccination.*,
                Antigen.name AS vaccine_name,
                Country.name AS country_name

            FROM Vaccination

            JOIN Antigen
                ON Vaccination.antigen =
                   Antigen.AntigenID

            JOIN Country
                ON Vaccination.country =
                   Country.CountryID

            WHERE Vaccination.country = ?
              AND Vaccination.year = ?
              AND Vaccination.antigen = ?
        """


        params = [
            country,
            year,
            antigen
        ]


        if region:

            query += """
                AND Country.region = ?
            """

            params.append(
                region
            )


        result = conn.execute(
            query,
            params
        ).fetchone()


        # =====================================================
        # COUNTRY CALCULATIONS
        # =====================================================

        if result:

            try:

                people_per_100 = float(
                    result["coverage"]
                )

                people_per_100 = round(
                    people_per_100,
                    2
                )

            except (TypeError, ValueError):

                people_per_100 = None


            try:

                target_population = int(
                    float(
                        result["target_num"]
                    )
                )

            except (TypeError, ValueError):

                target_population = None


            try:

                doses_administered = int(
                    float(
                        result["doses"]
                    )
                )

            except (TypeError, ValueError):

                doses_administered = None


            if people_per_100 is not None:

                if people_per_100 >= 90:

                    coverage_level = "Very High"

                elif people_per_100 >= 75:

                    coverage_level = "High"

                elif people_per_100 >= 50:

                    coverage_level = "Moderate"

                else:

                    coverage_level = "Low"


    # =========================================================
    # REGIONAL RESULT
    # =========================================================

    if region and year and antigen:

        regional_summary = conn.execute("""
            SELECT

                Region.region AS region_name,

                YearDate.YearID AS year,

                Antigen.name AS vaccine_name,

                COUNT(Vaccination.country) AS country_count,

                ROUND(
                    AVG(
                        CAST(
                            Vaccination.coverage AS REAL
                        )
                    ),
                    2
                ) AS average_coverage,

                SUM(
                    CASE
                        WHEN CAST(
                            Vaccination.coverage AS REAL
                        ) >= 90
                        THEN 1
                        ELSE 0
                    END
                ) AS countries_90

            FROM Vaccination

            JOIN Country
                ON Vaccination.country =
                   Country.CountryID

            JOIN Region
                ON Country.region =
                   Region.RegionID

            JOIN Antigen
                ON Vaccination.antigen =
                   Antigen.AntigenID

            JOIN YearDate
                ON Vaccination.year =
                   YearDate.YearID

            WHERE Country.region = ?
              AND Vaccination.year = ?
              AND Vaccination.antigen = ?

            GROUP BY

                Region.region,

                YearDate.YearID,

                Antigen.name

        """, (
            region,
            year,
            antigen
        )).fetchone()


        # =====================================================
        # REGIONAL COVERAGE
        # =====================================================

        if regional_summary:

            average_coverage = regional_summary[
                "average_coverage"
            ]


            if average_coverage is not None:

                if average_coverage >= 90:

                    regional_coverage_level = (
                        "Very High"
                    )

                    herd_immunity_status = (
                        "90% target reached"
                    )

                elif average_coverage >= 75:

                    regional_coverage_level = (
                        "High"
                    )

                    herd_immunity_status = (
                        "Below 90% target"
                    )

                elif average_coverage >= 50:

                    regional_coverage_level = (
                        "Moderate"
                    )

                    herd_immunity_status = (
                        "Below 90% target"
                    )

                else:

                    regional_coverage_level = (
                        "Low"
                    )

                    herd_immunity_status = (
                        "Below 90% target"
                    )


            # =================================================
            # CALCULATE 90% PERCENTAGE
            # =================================================

            total = regional_summary[
                "country_count"
            ]

            reached_90 = regional_summary[
                "countries_90"
            ]


            if total and reached_90 is not None:

                countries_90_percentage = round(
                    (
                        reached_90 / total
                    ) * 100,
                    2
                )


        # =====================================================
        # COUNTRIES REACHING 90%
        # =====================================================

        if regional_summary:

            countries_90 = conn.execute("""
                SELECT

                    Country.name AS country_name,

                    Vaccination.coverage

                FROM Vaccination

                JOIN Country
                    ON Vaccination.country =
                       Country.CountryID

                WHERE Country.region = ?

                  AND Vaccination.year = ?

                  AND Vaccination.antigen = ?

                  AND CAST(
                        Vaccination.coverage AS REAL
                      ) >= 90

                ORDER BY
                    CAST(
                        Vaccination.coverage AS REAL
                    ) DESC

            """, (
                region,
                year,
                antigen
            )).fetchall()


    conn.close()


    return render_template(
        "explore.html",

        regions=regions,

        countries=countries,

        years=years,

        antigens=antigens,

        result=result,

        coverage_level=coverage_level,

        people_per_100=people_per_100,

        target_population=target_population,

        doses_administered=doses_administered,

        regional_summary=regional_summary,

        regional_coverage_level=regional_coverage_level,

        herd_immunity_status=herd_immunity_status,

        countries_90=countries_90,

        countries_90_percentage=countries_90_percentage
    )


# =========================================================
# LEVEL 2B
# INFECTION DATA BY ECONOMIC STATUS
# =========================================================

@app.route("/infections")
def infections():

    conn = get_db_connection()


    # =========================================================
    # FILTERS
    # =========================================================

    economic_status = request.args.get(
        "economy",
        ""
    )

    infection_type = request.args.get(
        "infection",
        ""
    )

    year = request.args.get(
        "year",
        ""
    )


    # =========================================================
    # ECONOMIC STATUS OPTIONS
    # =========================================================

    economies = conn.execute("""
        SELECT
            economyID,
            phase
        FROM Economy
        ORDER BY economyID
    """).fetchall()


    # =========================================================
    # INFECTION TYPE OPTIONS
    # =========================================================

    infection_types = conn.execute("""
        SELECT
            id,
            description
        FROM Infection_Type
        ORDER BY description
    """).fetchall()


    # =========================================================
    # AVAILABLE YEARS
    # =========================================================

    years = conn.execute("""
        SELECT DISTINCT year
        FROM InfectionData
        ORDER BY year DESC
    """).fetchall()


    # =========================================================
    # LEVEL 2B RESULTS
    # =========================================================

    results = []
    summary_results = []


    if economic_status and infection_type and year:

        results = conn.execute("""
            SELECT

                c.name AS country,

                e.phase AS economic_status,

                it.description AS infection_type,

                i.year,

                i.cases,

                cp.population,

                ROUND(
                    (i.cases * 100000.0)
                    / cp.population,
                    2
                ) AS infection_rate

            FROM InfectionData i

            JOIN Country c
                ON i.country =
                   c.CountryID

            JOIN Economy e
                ON c.economy =
                   e.economyID

            JOIN Infection_Type it
                ON i.inf_type =
                   it.id

            JOIN CountryPopulation cp
                ON i.country =
                   cp.country

                AND i.year =
                    cp.year

            WHERE e.economyID = ?

              AND it.id = ?

              AND i.year = ?

              AND cp.population > 0

            ORDER BY i.cases DESC

        """, (
            economic_status,
            infection_type,
            year
        )).fetchall()

        summary_results = conn.execute("""
            SELECT
                e.phase AS economic_status,
                COUNT(DISTINCT i.country) AS country_count,
                SUM(i.cases) AS total_cases,
                ROUND(
                    SUM(i.cases) * 100000.0
                    / SUM(cp.population),
                    2
                ) AS combined_infection_rate
            FROM InfectionData i
            JOIN Country c
                ON i.country = c.CountryID
            JOIN Economy e
                ON c.economy = e.economyID
            JOIN Infection_Type it
                ON i.inf_type = it.id
            JOIN CountryPopulation cp
                ON i.country = cp.country
                AND i.year = cp.year
            WHERE it.id = ?
              AND i.year = ?
              AND cp.population > 0
            GROUP BY e.economyID, e.phase
            ORDER BY e.economyID
        """, (
            infection_type,
            year
        )).fetchall()


    conn.close()


    return render_template(
        "infections.html",

        economies=economies,

        infection_types=infection_types,

        years=years,

        results=results,

        selected_economy=economic_status,

        selected_infection=infection_type,

        selected_year=year,

        summary_results=summary_results,
    )


# =========================================================
# LEVEL 3B
# COUNTRIES ABOVE GLOBAL INFECTION RATE
# =========================================================

@app.route("/infection-analysis")
def infection_analysis():

    conn = get_db_connection()


    # =========================================================
    # FILTERS
    # =========================================================

    global_infection = request.args.get(
        "global_infection",
        ""
    )

    global_year = request.args.get(
        "global_year",
        ""
    )


    # =========================================================
    # INFECTION TYPES
    # =========================================================

    infection_types = conn.execute("""
        SELECT
            id,
            description
        FROM Infection_Type
        ORDER BY description
    """).fetchall()


    # =========================================================
    # YEARS
    # =========================================================

    years = conn.execute("""
        SELECT DISTINCT year
        FROM InfectionData
        ORDER BY year DESC
    """).fetchall()


    # =========================================================
    # DEFAULT VALUES
    # =========================================================

    global_results = []

    global_rate = None

    countries_above_global = 0


    # =========================================================
    # CALCULATE GLOBAL INFECTION RATE
    # =========================================================

    if global_infection and global_year:

        global_data = conn.execute("""
            SELECT

                SUM(i.cases) AS total_cases,

                SUM(cp.population)
                    AS total_population

            FROM InfectionData i

            JOIN CountryPopulation cp
                ON i.country =
                   cp.country

                AND i.year =
                    cp.year

            WHERE i.inf_type = ?

              AND i.year = ?

              AND cp.population > 0

        """, (
            global_infection,
            global_year
        )).fetchone()


        if (
            global_data["total_population"]
            and global_data["total_cases"]
            is not None
        ):

            global_rate = round(
                (
                    global_data["total_cases"]
                    * 100000.0
                )
                / global_data["total_population"],
                2
            )


            # =================================================
            # FIND COUNTRIES ABOVE GLOBAL RATE
            # =================================================

            global_results = conn.execute("""
            SELECT
                c.name AS country,
                e.phase AS economic_status,
                it.description AS infection_type,
                i.year,
                i.cases,
                cp.population,
                ROUND(
                    (i.cases * 100000.0)
                    / cp.population,
                    2
                ) AS infection_rate
            FROM InfectionData i
            JOIN Country c
                ON i.country = c.CountryID
            JOIN Economy e
                ON c.economy = e.economyID
            JOIN Infection_Type it
                ON i.inf_type = it.id
            JOIN CountryPopulation cp
                ON i.country = cp.country
                AND i.year = cp.year
            WHERE i.inf_type = ?
            AND i.year = ?
            AND cp.population > 0
            AND (
                    (i.cases * 100000.0)
                    / cp.population
                )
                >
                (
                    SELECT
                        SUM(i2.cases) * 100000.0
                        / SUM(cp2.population)
                    FROM InfectionData i2
                    JOIN CountryPopulation cp2
                        ON i2.country = cp2.country
                        AND i2.year = cp2.year
                    WHERE i2.inf_type = ?
                    AND i2.year = ?
                    AND cp2.population > 0
                )
            ORDER BY infection_rate DESC
        """, (
            global_infection,
            global_year,
            global_infection,
            global_year
        )).fetchall()


            countries_above_global = len(
                global_results
            )


    conn.close()


    return render_template(
        "infection_analysis.html",

        infection_types=infection_types,

        years=years,

        global_results=global_results,

        global_rate=global_rate,

        countries_above_global=(
            countries_above_global
        ),

        selected_global_infection=(
            global_infection
        ),

        selected_global_year=(
            global_year
        )
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


    # =========================================================
    # COUNTRIES
    # =========================================================

    countries = connection.execute("""
        SELECT
            CountryID,
            name
        FROM Country
        ORDER BY name
    """).fetchall()


    # =========================================================
    # VACCINES
    # =========================================================

    antigens = connection.execute("""
        SELECT
            AntigenID,
            name
        FROM Antigen
        ORDER BY name
    """).fetchall()


    # =========================================================
    # YEARS
    # =========================================================

    years = connection.execute("""
        SELECT
            YearID
        FROM YearDate
        ORDER BY YearID DESC
    """).fetchall()


    result1 = None

    result2 = None

    coverage_change = None

    comparison_message = None

    comparison_status = None


    # =========================================================
    # GET BOTH YEARS
    # =========================================================

    if country and antigen and year1 and year2:

        result1 = connection.execute("""
            SELECT *
            FROM Vaccination

            WHERE country = ?

              AND antigen = ?

              AND year = ?

              AND inf_type = ?

        """, (
            country,
            antigen,
            year1,
            "PER"
        )).fetchone()


        result2 = connection.execute("""
            SELECT *
            FROM Vaccination

            WHERE country = ?

              AND antigen = ?

              AND year = ?

              AND inf_type = ?

        """, (
            country,
            antigen,
            year2,
            "PER"
        )).fetchone()


    # =========================================================
    # CALCULATE CHANGE
    # =========================================================

    if result1 and result2:

        try:

            coverage1 = float(
                result1["coverage"]
            )

            coverage2 = float(
                result2["coverage"]
            )

            coverage_change = round(
                coverage2 - coverage1,
                2
            )

        except (ValueError, TypeError):

            coverage_change = None


    # =========================================================
    # COMPARISON MESSAGE
    # =========================================================

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

        comparison_message=(
            comparison_message
        ),

        comparison_status=(
            comparison_status
        )

    )


# =========================================================
# LEVEL 3A
# BIGGEST IMPROVEMENT IN VACCINATION RATES
# =========================================================

@app.route("/trends")
def trends():

    conn = get_db_connection()


    start_year = request.args.get(
        "start_year",
        ""
    )

    end_year = request.args.get(
        "end_year",
        ""
    )

    antigen = request.args.get(
        "antigen",
        ""
    )

    limit = request.args.get(
        "limit",
        "10"
    )


    # =========================================================
    # YEARS
    # =========================================================

    years = conn.execute("""
        SELECT DISTINCT YearID
        FROM YearDate
        ORDER BY YearID DESC
    """).fetchall()


    # =========================================================
    # ANTIGENS
    # =========================================================

    antigens = conn.execute("""
        SELECT
            AntigenID,
            name
        FROM Antigen
        ORDER BY name
    """).fetchall()


    results = []

    total_countries = 0


    # =========================================================
    # CHECK LIMIT
    # =========================================================

    try:

        limit = int(limit)

        if limit not in [
            5,
            10,
            20,
            50
        ]:

            limit = 10

    except ValueError:

        limit = 10


    # =========================================================
    # FIND BIGGEST IMPROVEMENT
    # =========================================================

    if start_year and end_year and antigen:

        results = conn.execute("""
            SELECT

                c.name AS country,

                start_data.coverage
                    AS start_coverage,

                end_data.coverage
                    AS end_coverage,

                ROUND(
                    end_data.coverage
                    - start_data.coverage,
                    2
                ) AS improvement

            FROM Vaccination start_data

            JOIN Vaccination end_data

                ON start_data.country =
                   end_data.country

                AND start_data.antigen =
                    end_data.antigen

            JOIN Country c

                ON start_data.country =
                   c.CountryID

            WHERE start_data.year = ?

              AND end_data.year = ?

              AND start_data.antigen = ?

              AND start_data.coverage
                  IS NOT NULL

              AND end_data.coverage
                  IS NOT NULL

            ORDER BY improvement DESC

            LIMIT ?

        """, (
            start_year,
            end_year,
            antigen,
            limit
        )).fetchall()


        total_countries = len(
            results
        )


    conn.close()


    return render_template(

        "trends.html",

        years=years,

        antigens=antigens,

        results=results,

        total_countries=(
            total_countries
        ),

        selected_start_year=(
            start_year
        ),

        selected_end_year=(
            end_year
        ),

        selected_antigen=(
            antigen
        ),

        selected_limit=(
            limit
        )

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