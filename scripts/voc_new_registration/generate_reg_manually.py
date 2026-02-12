
# poetry run python manage.py shell

from voc_new_registration.models import NewRegistration, RegistrationPayment
from voc_new_registration.utils.registration_logic import generate_registration_number

# 1. Get the payment record
order_id = "REG_B9A3BC51E0CD"
payment = RegistrationPayment.objects.select_related('registration').get(order_id=order_id)

# 2. Sync registration data
reg = payment.registration

if not reg.registration_number:
    print(f"Generating registration number for {reg.student_name}...")
    # This generates the number and saves it to the database
    reg.registration_number = generate_registration_number(reg)
    print(f"Number Generated: {reg.registration_number}")

# 3. Mark as completed
reg.is_registration_completed = True
reg.save(update_fields=['is_registration_completed', 'registration_number', 'sr_no'])

print(f"Success! Registration {reg.registration_number} is now marked as COMPLETED.")
