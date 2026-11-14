
import httpx
import uuid
from datetime import date, datetime

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 15


def get_items(data, possible_keys):
    """Extract a list from different possible API response formats."""
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in possible_keys:
            value = data.get(key)
            if isinstance(value, list):
                return value

    return []


def check(label, condition):
    if condition:
        print(f"[PASS] {label}")
    else:
        print(f"[FAIL] {label}")

    return condition


def get_expiry_date(product):
    value = product.get("expiry_date")

    if not value:
        return None

    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def main():
    print("\n======================================")
    print("       FOODRESCUE WORKFLOW TEST")
    print("======================================\n")

    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:

        # --------------------------------------------------
        # 1. BACKEND CONNECTION
        # --------------------------------------------------

        try:
            response = client.get("/health")
        except httpx.RequestError as error:
            print("[FAIL] Backend connection")
            print("Could not connect:", error)
            return

        if not check("Backend connection", response.status_code == 200):
            print(response.text)
            return

        # --------------------------------------------------
        # 2. INVENTORY API
        # --------------------------------------------------

        response = client.get("/api/inventory")

        if not check("Inventory API", response.status_code == 200):
            print(response.text)
            return

        inventory = get_items(
            response.json(),
            ["inventory", "items", "data"]
        )

        print(f"\nInventory products found: {len(inventory)}")
        print("\n========== INVENTORY ==========")

        for product in inventory:
            print(
                "Product:", product.get("name"),
                "| ID:", product.get("product_id", product.get("id")),
                "| Quantity:", product.get("quantity"),
                "| Safety:", product.get("safety_status"),
                "| Expiry:", product.get("expiry_date")
            )

        # --------------------------------------------------
        # 3. DONATIONS API
        # --------------------------------------------------

        response = client.get("/api/donations")

        if not check("Donations API", response.status_code == 200):
            print(response.text)
            return

        donations = get_items(
            response.json(),
            ["donations", "items", "data"]
        )

        # --------------------------------------------------
        # 4. NGO API
        # --------------------------------------------------

        response = client.get("/api/ngos")

        if not check("NGO API", response.status_code == 200):
            print(response.text)
            return

        ngos = get_items(
            response.json(),
            ["ngos", "items", "data"]
        )

        print(f"\nDonations found: {len(donations)}")
        print(f"NGOs found: {len(ngos)}")

        print("\n========== NGO DETAILS ==========")

        active_ngos = []

        for ngo in ngos:
            active = ngo.get(
                "is_active",
                ngo.get("active", False)
            )

            ngo_id = ngo.get("ngo_id", ngo.get("id"))

            print(
                "Name:", ngo.get("name"),
                "| ID:", ngo_id,
                "| Active:", active,
                "| Capacity:", ngo.get(
                    "capacity",
                    ngo.get("available_capacity", "Unknown")
                )
            )

            if active and ngo_id:
                active_ngos.append(ngo)

        if not active_ngos:
            print("\n[FAIL] No active NGO available.")
            return

        # --------------------------------------------------
        # 5. FIND AN EXISTING PENDING DONATION
        # --------------------------------------------------

        pending = next(
            (
                donation for donation in donations
                if str(donation.get("status", "")).lower()
                == "pending"
            ),
            None
        )

        if pending:
            print("\n[INFO] Existing pending donation found.")

        else:
            print("\n[INFO] No pending donation available.")

            # Find a verified, unexpired product with stock.
            eligible_products = []

            for product in inventory:
                quantity = product.get("quantity", 0)

                try:
                    quantity = int(quantity)
                except (ValueError, TypeError):
                    continue

                expiry = get_expiry_date(product)

                if (
                    str(product.get("safety_status", "")).lower()
                    == "verified"
                    and expiry is not None
                    and expiry >= date.today()
                    and quantity >= 1
                ):
                    eligible_products.append(product)

            if not eligible_products:
                print(
                    "[FAIL] No verified, unexpired product "
                    "with available stock."
                )
                return

            print("\n========== ELIGIBLE PRODUCTS ==========")

            for product in eligible_products:
                print(
                    product.get("name"),
                    "| Quantity:", product.get("quantity"),
                    "| Expiry:", product.get("expiry_date")
                )

            selected = eligible_products[0]

            print("\nSelected product:", selected.get("name"))
            print("Test donation quantity: 1 unit")

            answer = input(
                "\nCreate a test donation and deduct 1 unit "
                "from inventory? (yes/no): "
            ).strip().lower()

            if answer not in ("yes", "y"):
                print("\n[STOPPED] No donation was created.")
                print("No inventory was changed.")
                return

            product_id = selected.get(
                "product_id",
                selected.get("id")
            )

            if product_id is None:
                print("[FAIL] Product ID is missing.")
                return

            payload = {
                "donation_id": "TEST_" + uuid.uuid4().hex[:10].upper(),
                "product_id": str(product_id),
                "quantity": 1,
                "note": "Automated FoodRescue workflow test"
            }

            response = client.post(
                "/api/donations",
                json=payload
            )

            if response.status_code not in (200, 201):
                print("\n[FAIL] Test donation creation")
                print("HTTP status:", response.status_code)
                print("Response:", response.text)
                return

            print("\n[PASS] Test donation created")

            created = response.json()

            # Use the returned donation, or retrieve it again.
            donation_id = created.get(
                "donation_id",
                payload["donation_id"]
            )

            pending = {
                **payload,
                **created,
                "donation_id": donation_id
            }

        # --------------------------------------------------
        # 6. MATCH DONATION WITH AN ACTIVE NGO
        # --------------------------------------------------

        donation_id = pending.get("donation_id")

        if not donation_id:
            print("[FAIL] Donation ID is missing.")
            return

        if str(pending.get("status", "")).lower() == "accepted":
            print(
                "\n[INFO] This donation is already accepted. "
                "Matching test skipped."
            )
            return

        selected_ngo = active_ngos[0]

        ngo_id = selected_ngo.get(
            "ngo_id",
            selected_ngo.get("id")
        )

        print("\n========== MATCHING ==========")
        print("Donation ID:", donation_id)
        print("NGO:", selected_ngo.get("name"))
        print("NGO ID:", ngo_id)

        response = client.post(
            f"/api/donations/{donation_id}/match",
            params={"ngo_id": ngo_id}
        )

        if response.status_code not in (200, 201):
            print("\n[FAIL] NGO matching")
            print("HTTP status:", response.status_code)
            print("Response:", response.text)
            print(
                "\nThe donation may still be pending. "
                "Check the backend response before retrying."
            )
            return

        print("\n[PASS] NGO matching request")

        # --------------------------------------------------
        # 7. VERIFY DONATION STATUS
        # --------------------------------------------------

        response = client.get("/api/donations")

        if response.status_code != 200:
            print("[FAIL] Could not verify donation status.")
            print(response.text)
            return

        updated_donations = get_items(
            response.json(),
            ["donations", "items", "data"]
        )

        updated = next(
            (
                donation for donation in updated_donations
                if str(donation.get("donation_id"))
                == str(donation_id)
            ),
            None
        )

        if not updated:
            print("[FAIL] Matched donation not found.")
            return

        accepted = (
            str(updated.get("status", "")).lower()
            == "accepted"
        )

        check("Donation status is accepted", accepted)

        if not accepted:
            print("Current status:", updated.get("status"))
            return

        # --------------------------------------------------
        # 8. TEST DUPLICATE MATCHING PROTECTION
        # --------------------------------------------------

        response = client.post(
            f"/api/donations/{donation_id}/match",
            params={"ngo_id": ngo_id}
        )

        check(
            "Duplicate matching is rejected",
            response.status_code == 409
        )

        if response.status_code != 409:
            print("Duplicate response:", response.status_code)
            print(response.text)

        # --------------------------------------------------
        # 9. TEST ACCEPTED DONATION DELETION PROTECTION
        # --------------------------------------------------

        response = client.delete(
            f"/api/donations/{donation_id}"
        )

        check(
            "Accepted donation deletion is blocked",
            400 <= response.status_code < 500
        )

        # --------------------------------------------------
        # 10. FINAL RESULT
        # --------------------------------------------------

        print("\n======================================")
        print("          WORKFLOW TEST FINISHED")
        print("======================================")

        print("Donation ID:", donation_id)
        print("Final donation status: accepted")
        print("Matched NGO:", selected_ngo.get("name"))

        print(
            "\nIMPORTANT: The accepted donation has not been "
            "deleted or reversed."
        )


if __name__ == "__main__":
    main()
