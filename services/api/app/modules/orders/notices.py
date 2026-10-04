"""Original multilingual reason-code catalogue (BR-44). No generated explanation claims."""

from typing import Literal

Language = Literal["en", "si", "ta"]

REASONS = {
    "NO_REEFER_CAPACITY": (
        "Refrigerated trucks are full on this run.",
        "මෙම ගමනේ ශීතකරණ වාහනවල ඉඩ පිරී ඇත.",
        "இந்தப் பயணத்தில் குளிரூட்டப்பட்ட வாகனங்கள் நிரம்பியுள்ளன.",
    ),
    "NO_VAN_AVAILABLE": (
        "No suitable van is available.",
        "සුදුසු වෑන් රථයක් ලබා ගත නොහැක.",
        "பொருத்தமான வேன் கிடைக்கவில்லை.",
    ),
    "VOLUME_CAP": (
        "The available vehicle space is full.",
        "ලබා ගත හැකි වාහන ඉඩ පිරී ඇත.",
        "கிடைக்கும் வாகன இடம் நிரம்பியுள்ளது.",
    ),
    "WEIGHT_CAP": (
        "The vehicle weight limit has been reached.",
        "වාහනයේ බර සීමාවට ළඟා වී ඇත.",
        "வாகனத்தின் எடை வரம்பு எட்டப்பட்டுள்ளது.",
    ),
    "FRESH_TIME_BUDGET": (
        "The morning delivery time is fully allocated.",
        "උදෑසන බෙදාහැරීමේ කාලය සම්පූර්ණයෙන් වෙන් කර ඇත.",
        "காலை விநியோக நேரம் முழுமையாக ஒதுக்கப்பட்டுள்ளது.",
    ),
    "DAY_TIME_BUDGET": (
        "The daytime delivery time is fully allocated.",
        "දිවා බෙදාහැරීමේ කාලය සම්පූර්ණයෙන් වෙන් කර ඇත.",
        "பகல் விநியோக நேரம் முழுமையாக ஒதுக்கப்பட்டுள்ளது.",
    ),
    "TRIP_LIMIT": (
        "Available vehicles have reached their trip limit.",
        "වාහනවල ගමන් වාර සීමාවට ළඟා වී ඇත.",
        "வாகனங்கள் பயண வரம்பை எட்டியுள்ளன.",
    ),
    "FUEL_QUOTA": (
        "The remaining fuel quota cannot cover this delivery.",
        "ඉතිරි ඉන්ධන ප්‍රමාණය මෙම බෙදාහැරීමට ප්‍රමාණවත් නොවේ.",
        "மீதமுள்ள எரிபொருள் ஒதுக்கீடு இந்த விநியோகத்திற்குப் போதாது.",
    ),
    "VEHICLE_UNAVAILABLE": (
        "A suitable vehicle is unavailable.",
        "සුදුසු වාහනයක් ලබා ගත නොහැක.",
        "பொருத்தமான வாகனம் கிடைக்கவில்லை.",
    ),
    "LOWER_PRIORITY": (
        "Another order has higher priority on this run.",
        "මෙම ගමනේ වෙනත් ඇණවුමකට වැඩි ප්‍රමුඛතාවයක් ඇත.",
        "இந்தப் பயணத்தில் மற்றொரு ஆர்டருக்கு அதிக முன்னுரிமை உள்ளது.",
    ),
}

SOURCE = ("Written from the plan", "සැලැස්මෙන් ලියන ලදී", "திட்டத்திலிருந்து எழுதப்பட்டது")
PROTECTION = (
    "First in line (moved once)",
    "පළමු ප්‍රමුඛතාවය (වරක් කල් දැමූ)",
    "முதல் முன்னுரிமை (ஒருமுறை மாற்றப்பட்டது)",
)
TITLE = ("Delivery update", "බෙදාහැරීමේ යාවත්කාලීනය", "விநியோகப் புதுப்பிப்பு")


def language_index(language: Language) -> int:
    return {"en": 0, "si": 1, "ta": 2}[language]
