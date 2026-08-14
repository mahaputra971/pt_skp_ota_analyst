import os
import smtplib
import time
import random

from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage


# =========================================================
# LOAD ENVIRONMENT VARIABLE
# =========================================================

load_dotenv()


# =========================================================
# KONFIGURASI EMAIL PENGIRIM
# =========================================================

SENDER_EMAIL = "marcom@daunlebarubud.com"

SENDER_PASSWORD = os.getenv(
    "PASSWORD_EMAIL_KANTOR"
)


# =========================================================
# KONFIGURASI SMTP HOSTINGER
# =========================================================

SMTP_HOST = "smtp.hostinger.com"
SMTP_PORT = 465


# =========================================================
# LINK VIDEO / PROMO
# =========================================================

VIDEO_LINK = "https://tinyurl.com/dlvoffers"


# =========================================================
# LOGO
# =========================================================

LOGO_FILE = "special_offers.png"


# =========================================================
# CC
# =========================================================
#
# Bisa menambahkan lebih dari satu alamat CC.
#
# Contoh:
#
# CC_LIST = [
#     "manager@domain.com",
#     "sales@domain.com"
# ]
#
# =========================================================

CC_LIST = [
    "sales@daunlebarubud.com",
    "marija09.skp@gmail.com"
]


# =========================================================
# DAFTAR OFFLINE TRAVEL AGENT
# =========================================================
#
# Ganti data di bawah dengan data Travel Agent sebenarnya.
#
# "name"  = Nama Travel Agent
# "email" = Email Travel Agent
#
# Nama akan otomatis digunakan di:
#
# 1. Subject
# 2. Greeting
# 3. Isi email
# 4. Closing
#
# =========================================================

TRAVEL_AGENTS = [

    {
        "name": "nama travel agent 1",
        "email": "anandamahaputra.skp@gmail.com"
    },

    # {
    #     "name": "nama travel agent 2",
    #     "email": "emailagent2@example.com"
    # },

    # {
    #     "name": "nama travel agent 3",
    #     "email": "emailagent3@example.com"
    # },

]


# =========================================================
# SUBJECT EMAIL
# =========================================================

SUBJECT_TEMPLATE = (
    "Exclusive August Offers for {agent_name} "
    "| Daun Lebar Villas Ubud"
)


# =========================================================
# HTML EMAIL TEMPLATE
# =========================================================
#
# Placeholder:
#
# {agent_name}
# {video_link}
#
# akan otomatis diganti oleh program.
#
# =========================================================

HTML_BODY_TEMPLATE = """

<!DOCTYPE html>

<html>

<head>

    <meta charset="UTF-8">

    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">

    <title>
        Daun Lebar Villas - August Offers
    </title>

</head>


<body style="
    margin: 0;
    padding: 0;
    background-color: #f4f4f2;
    font-family: Arial, Helvetica, sans-serif;
    color: #45464A;
">


    <!-- =====================================================
         OUTER CONTAINER
         ===================================================== -->

    <div style="
        width: 100%;
        margin: 0;
        padding: 30px 0;
        background-color: #f4f4f2;
    ">


        <!-- =================================================
             MAIN CARD
             ================================================= -->

        <div style="
            max-width: 650px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 12px;
            overflow: hidden;
        ">


            <!-- =============================================
                 LOGO SECTION
                 ============================================= -->

            <div style="
                padding: 24px 30px 14px;
                text-align: center;
                background-color: #ffffff;
            ">

                <img
                    src="cid:special_offers"
                    alt="Daun Lebar Villas"
                    width="165"
                    style="
                        width: 165px;
                        max-width: 165px;
                        height: auto;
                        display: inline-block;
                        border: 0;
                        outline: none;
                        text-decoration: none;
                    "
                >

            </div>



            <!-- =============================================
                 HEADER
                 ============================================= -->

            <div style="
                padding: 28px 30px 32px;
                text-align: center;
                background-color: #EEF0E5;
                border-top: 1px solid #E3E5D7;
                border-bottom: 1px solid #E3E5D7;
            ">


                <!-- BRAND -->

                <div style="
                    font-size: 11px;
                    letter-spacing: 2.5px;
                    color: #6F7547;
                    margin-bottom: 10px;
                    font-weight: 600;
                ">

                    DAUN LEBAR VILLAS UBUD

                </div>



                <!-- TITLE -->

                <h1 style="
                    margin: 0;
                    color: #45464A;
                    font-size: 29px;
                    line-height: 1.3;
                    font-weight: 600;
                ">

                    Special August Offers

                </h1>



                <!-- SUBTITLE -->

                <p style="
                    margin: 10px 0 0;
                    color: #777777;
                    font-size: 14px;
                    line-height: 1.5;
                ">

                    Exclusive Offers for Our
                    Travel Agent Partners

                </p>


            </div>



            <!-- =============================================
                 EMAIL CONTENT
                 ============================================= -->

            <div style="
                padding: 35px 30px;
            ">


                <!-- =========================================
                     GREETING
                     ========================================= -->

                <p style="
                    margin: 0 0 18px;
                    font-size: 16px;
                    line-height: 1.6;
                    color: #45464A;
                ">

                    Dear
                    <strong>{agent_name} Team</strong>,

                </p>



                <!-- =========================================
                     INTRODUCTION
                     ========================================= -->

                <p style="
                    font-size: 15px;
                    line-height: 1.8;
                    margin: 0 0 16px;
                    color: #555555;
                ">

                    Warm greetings from
                    <strong style="color: #6F7547;">
                        Daun Lebar Villas Ubud
                    </strong>.

                </p>


                <p style="
                    font-size: 15px;
                    line-height: 1.8;
                    margin: 0 0 16px;
                    color: #555555;
                ">

                    We are pleased to share our
                    <strong style="color: #6F7547;">
                        Special August Offers
                    </strong>,
                    prepared exclusively for our valued
                    <strong>
                        Offline Travel Agent partners
                    </strong>.

                </p>


                <p style="
                    font-size: 15px;
                    line-height: 1.8;
                    margin: 0 0 25px;
                    color: #555555;
                ">

                    We would love to invite
                    <strong style="color: #6F7547;">
                        {agent_name}
                    </strong>
                    to take advantage of these special
                    opportunities and offer your clients
                    an unforgettable stay experience
                    at Daun Lebar Villas.

                </p>



                <!-- =========================================
                     AUGUST OFFER / VIDEO CTA
                     ========================================= -->

                <div style="
                    margin: 30px 0;
                    padding: 30px 25px;
                    text-align: center;
                    background-color: #F5F7EE;
                    border-radius: 10px;
                    border: 1px solid #E1E4D2;
                ">


                    <!-- LABEL -->

                    <div style="
                        font-size: 11px;
                        letter-spacing: 2px;
                        color: #6F7547;
                        margin-bottom: 10px;
                        font-weight: 600;
                    ">

                        AUGUST SPECIAL

                    </div>



                    <!-- TITLE -->

                    <h2 style="
                        margin: 0 0 12px;
                        color: #45464A;
                        font-size: 21px;
                        line-height: 1.4;
                        font-weight: 600;
                    ">

                        Discover Our Latest Offers

                    </h2>



                    <!-- DESCRIPTION -->

                    <p style="
                        margin: 0 auto 22px;
                        max-width: 470px;
                        color: #666666;
                        font-size: 14px;
                        line-height: 1.7;
                    ">

                        Explore our latest August promotions
                        and special offers prepared especially
                        for our Travel Agent partners.

                    </p>



                    <!-- =====================================
                         MAIN BUTTON
                         ===================================== -->

                    <a
                        href="{video_link}"
                        target="_blank"
                        style="
                            display: inline-block;
                            padding: 13px 28px;
                            background-color: #6F7547;
                            color: #ffffff;
                            text-decoration: none;
                            border-radius: 5px;
                            font-size: 13px;
                            font-weight: 600;
                            letter-spacing: 0.8px;
                        "
                    >

                        VIEW AUGUST OFFERS

                    </a>



                    <!-- BUTTON DESCRIPTION -->

                    <p style="
                        margin: 15px 0 0;
                        color: #999999;
                        font-size: 12px;
                        line-height: 1.5;
                    ">

                        Click the button above to view
                        the latest offer details.

                    </p>


                </div>



                <!-- =========================================
                     PARTNERSHIP SECTION
                     ========================================= -->

                <h3 style="
                    margin: 30px 0 12px;
                    color: #6F7547;
                    font-size: 18px;
                    line-height: 1.4;
                    font-weight: 600;
                ">

                    Let's Work Together

                </h3>



                <p style="
                    font-size: 15px;
                    line-height: 1.8;
                    margin: 0 0 16px;
                    color: #555555;
                ">

                    At Daun Lebar Villas, we highly value our
                    relationships with Travel Agent partners.
                    We believe that a strong partnership can
                    create a better experience for both our
                    partners and their clients.

                </p>



                <p style="
                    font-size: 15px;
                    line-height: 1.8;
                    margin: 0 0 25px;
                    color: #555555;
                ">

                    If you have clients looking for a private,
                    comfortable and memorable villa experience
                    in Ubud, our team would be happy to assist
                    with your booking requirements.

                </p>



                <!-- =========================================
                     CLOSING
                     ========================================= -->

                <p style="
                    font-size: 15px;
                    line-height: 1.8;
                    margin: 0 0 8px;
                    color: #555555;
                ">

                    We look forward to creating
                    more successful bookings together
                    with
                    <strong style="color: #6F7547;">
                        {agent_name}
                    </strong>.

                </p>



                <p style="
                    font-size: 15px;
                    line-height: 1.8;
                    margin: 25px 0 0;
                    color: #555555;
                ">

                    Warm regards,<br>

                    <strong style="color: #45464A;">
                        Marketing Team
                    </strong><br>

                    <span style="color: #6F7547;">
                        Daun Lebar Villas Ubud
                    </span>

                </p>


            </div>



            <!-- =============================================
                 FOOTER
                 ============================================= -->

            <div style="
                padding: 20px;
                text-align: center;
                background-color: #EEF0E5;
                color: #777777;
                font-size: 11px;
                line-height: 1.6;
                border-top: 1px solid #E1E4D2;
            ">


                <strong style="
                    color: #6F7547;
                    letter-spacing: 0.5px;
                ">

                    Daun Lebar Villas Ubud

                </strong>


                <br>


                Exclusive August Offers
                for Travel Agent Partners


            </div>


        </div>


    </div>


</body>

</html>

"""


# =========================================================
# VALIDASI KONFIGURASI
# =========================================================

def validate_configuration():

    # -----------------------------------------------------
    # PASSWORD
    # -----------------------------------------------------

    if not SENDER_PASSWORD:

        raise ValueError(
            "\n"
            "PASSWORD_EMAIL_KANTOR tidak ditemukan.\n\n"
            "Pastikan file .env berada di folder yang sama "
            "dengan email_bot.py.\n\n"
            "Isi .env dengan:\n"
            "PASSWORD_EMAIL_KANTOR=password_email_kamu\n"
        )


    # -----------------------------------------------------
    # TRAVEL AGENT
    # -----------------------------------------------------

    if not TRAVEL_AGENTS:

        raise ValueError(
            "TRAVEL_AGENTS masih kosong."
        )


    # -----------------------------------------------------
    # LOGO
    # -----------------------------------------------------

    if not os.path.isfile(LOGO_FILE):

        raise FileNotFoundError(
            f"\nFile logo tidak ditemukan: "
            f"{LOGO_FILE}\n\n"
            f"Pastikan file {LOGO_FILE} "
            f"berada di folder yang sama "
            f"dengan email_bot.py.\n"
        )


    # -----------------------------------------------------
    # VALIDASI SETIAP AGENT
    # -----------------------------------------------------

    for agent in TRAVEL_AGENTS:

        if not agent.get("name"):

            raise ValueError(
                "Ada Travel Agent yang tidak memiliki nama."
            )


        if not agent.get("email"):

            raise ValueError(
                f"Travel Agent "
                f"{agent.get('name')} "
                f"tidak memiliki email."
            )


# =========================================================
# MEMBUAT HTML BODY
# =========================================================

def create_email_body(agent_name):

    return HTML_BODY_TEMPLATE.format(

        agent_name=agent_name,

        video_link=VIDEO_LINK

    )


# =========================================================
# MEMBUAT EMAIL MESSAGE
# =========================================================

def create_message(agent):

    receiver = agent["email"]

    agent_name = agent["name"]


    # -----------------------------------------------------
    # SUBJECT
    # -----------------------------------------------------

    subject = SUBJECT_TEMPLATE.format(

        agent_name=agent_name

    )


    # -----------------------------------------------------
    # HTML BODY
    # -----------------------------------------------------

    html_body = create_email_body(

        agent_name

    )


    # =====================================================
    # RELATED MESSAGE
    #
    # Digunakan karena logo merupakan inline image.
    # =====================================================

    msg = MIMEMultipart(

        "related"

    )


    # -----------------------------------------------------
    # HEADER
    # -----------------------------------------------------

    msg["Subject"] = subject

    msg["From"] = SENDER_EMAIL

    msg["To"] = receiver


    # -----------------------------------------------------
    # CC
    # -----------------------------------------------------

    if CC_LIST:

        msg["Cc"] = ", ".join(

            CC_LIST

        )


    # =====================================================
    # ALTERNATIVE PART
    # =====================================================

    alternative = MIMEMultipart(

        "alternative"

    )


    msg.attach(

        alternative

    )


    # -----------------------------------------------------
    # HTML
    # -----------------------------------------------------

    alternative.attach(

        MIMEText(

            html_body,

            "html",

            "utf-8"

        )

    )


    # =====================================================
    # INLINE LOGO
    # =====================================================

    try:

        with open(

            LOGO_FILE,

            "rb"

        ) as logo_file:

            logo_data = logo_file.read()


    except Exception as error:

        raise FileNotFoundError(

            f"Gagal membaca logo "
            f"{LOGO_FILE}: {error}"

        )


    # -----------------------------------------------------
    # MIME IMAGE
    # -----------------------------------------------------

    logo = MIMEImage(

        logo_data

    )


    # -----------------------------------------------------
    # CONTENT ID
    # -----------------------------------------------------

    logo.add_header(

        "Content-ID",

        "<special_offers>"

    )


    # -----------------------------------------------------
    # INLINE DISPOSITION
    # -----------------------------------------------------

    logo.add_header(

        "Content-Disposition",

        "inline",

        filename="special_offers.png"

    )


    # -----------------------------------------------------
    # ATTACH LOGO
    # -----------------------------------------------------

    msg.attach(

        logo

    )


    return msg


# =========================================================
# MAIN EMAIL BOT
# =========================================================

def run_email_bot():

    print()

    print(
        "=================================================="
    )

    print(
        "       BOT EMAIL OTOMATIS HOSTINGER"
    )

    print(
        "       DAUN LEBAR VILLAS UBUD"
    )

    print(
        "=================================================="
    )

    print()


    # =====================================================
    # VALIDASI
    # =====================================================

    try:

        validate_configuration()


    except Exception as error:

        print(
            "[ERROR CONFIGURATION]"
        )

        print(

            error

        )

        return


    # =====================================================
    # INFORMASI BOT
    # =====================================================

    print(

        f"[INFO] Sender : "
        f"{SENDER_EMAIL}"

    )


    print(

        f"[INFO] SMTP   : "
        f"{SMTP_HOST}:{SMTP_PORT}"

    )


    print(

        f"[INFO] Agent  : "
        f"{len(TRAVEL_AGENTS)}"

    )


    print(

        f"[INFO] Logo   : "
        f"{LOGO_FILE}"

    )


    if CC_LIST:

        print(

            f"[INFO] CC     : "
            f"{', '.join(CC_LIST)}"

        )

    else:

        print(

            "[INFO] CC     : Tidak ada"

        )


    print()


    # =====================================================
    # CONNECT SMTP
    # =====================================================

    try:

        print(

            "[INIT] Menghubungkan ke "
            "server Hostinger..."

        )


        server = smtplib.SMTP_SSL(

            SMTP_HOST,

            SMTP_PORT,

            timeout=30

        )


        print(

            "[INIT] Melakukan autentikasi..."

        )


        server.login(

            SENDER_EMAIL,

            SENDER_PASSWORD

        )


        print(

            "[SUKSES] Login Hostinger berhasil!"

        )


        print()


    except Exception as error:

        print()


        print(

            "[ERROR FATAL] "
            "Gagal terhubung/login "
            "ke Hostinger:"

        )


        print(

            error

        )


        print()


        return


    # =====================================================
    # COUNTER
    # =====================================================

    success_count = 0

    failed_count = 0


    # =====================================================
    # LOOP TRAVEL AGENT
    # =====================================================

    for index, agent in enumerate(

        TRAVEL_AGENTS,

        start=1

    ):


        receiver = agent["email"]

        agent_name = agent["name"]


        print(

            "--------------------------------------------------"

        )


        print(

            f"[{index}/{len(TRAVEL_AGENTS)}] "
            f"Processing: {agent_name}"

        )


        print(

            f"       Email: {receiver}"

        )


        try:

            # ---------------------------------------------
            # CREATE EMAIL
            # ---------------------------------------------

            msg = create_message(

                agent

            )


            # ---------------------------------------------
            # TO + CC
            # ---------------------------------------------

            all_recipients = [

                receiver

            ] + CC_LIST


            # ---------------------------------------------
            # SEND
            # ---------------------------------------------

            server.sendmail(

                SENDER_EMAIL,

                all_recipients,

                msg.as_string()

            )


            success_count += 1


            print(

                f"[V] Berhasil dikirim ke "
                f"{agent_name}"

            )


            print(

                f"    TO : {receiver}"

            )


            if CC_LIST:

                print(

                    f"    CC : "
                    f"{', '.join(CC_LIST)}"

                )


        except Exception as error:

            failed_count += 1


            print(

                f"[X] Gagal mengirim ke "
                f"{agent_name}"

            )


            print(

                f"    Error: {error}"

            )


        # =================================================
        # RANDOM DELAY
        # =================================================
        #
        # Tidak ada delay setelah email terakhir.
        #
        # =================================================

        if index < len(

            TRAVEL_AGENTS

        ):


            delay = random.uniform(

                5,

                12

            )


            print()


            print(

                f"[WAIT] Menunggu "
                f"{delay:.1f} detik..."

            )


            time.sleep(

                delay

            )


    # =====================================================
    # CLOSE SMTP CONNECTION
    # =====================================================

    try:

        server.quit()


    except Exception:

        pass


    # =====================================================
    # SUMMARY
    # =====================================================

    print()

    print(

        "=================================================="

    )


    print(

        "                 SELESAI"

    )


    print(

        "=================================================="

    )


    print(

        f"Total Travel Agent : "
        f"{len(TRAVEL_AGENTS)}"

    )


    print(

        f"Berhasil           : "
        f"{success_count}"

    )


    print(

        f"Gagal              : "
        f"{failed_count}"

    )


    print(

        "=================================================="

    )


# =========================================================
# PROGRAM ENTRY POINT
# =========================================================

if __name__ == "__main__":

    run_email_bot()