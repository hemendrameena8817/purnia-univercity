# Grievance Payment Integration

## Overview
The grievance system now requires payment before a grievance number is generated and the grievance becomes active. This follows the same payment flow as the VOC registration system using CC Avenue payment gateway.

## Payment Flow

### 1. Student Creates Grievance Draft
- Student fills out grievance details (category, subject, description, attachments)
- Grievance is created in the database **without a grievance_number**
- `is_payment_completed = False`
- Returns grievance UID for payment initiation

### 2. Payment Initiation
**Endpoint:** `POST /api/grievances/{grievance_uid}/initiate-payment/`

**Request:** No body required (authenticated request)

**Response:**
```json
{
  "order_id": "GRV_ABC123456789",
  "enc_request": "encrypted_payment_data",
  "access_code": "AVXXX",
  "production_url": "https://test.ccavenue.com/transaction/transaction.do?command=initiateTransaction"
}
```

**Process:**
- Validates grievance exists and belongs to the user
- Checks payment not already completed
- Creates `GrievancePayment` record with status `PENDING`
- Fixed amount: ₹100.00
- Generates unique order_id: `GRV_{12_char_hex}`
- Encrypts payment data using CC Avenue working key
- Returns encrypted data for frontend to submit to payment gateway

### 3. Payment Gateway Processing
- Frontend submits encrypted data to CC Avenue
- User completes payment on CC Avenue portal
- CC Avenue redirects back to: `/api/grievances/payment-response/`

### 4. Payment Response Handling
**Endpoint:** `POST /api/grievances/payment-response/`

**Process:**
- Receives encrypted response from CC Avenue
- Decrypts response using working key
- Updates `GrievancePayment` record with transaction details
- **On SUCCESS:**
  - Sets `grievance.is_payment_completed = True`
  - Triggers automatic `grievance_number` generation (GRV000001 format)
  - Grievance becomes active
- **On FAILURE/ABORTED:**
  - Updates payment status
  - Grievance remains in draft state
- Redirects to frontend: `/grievances/payment-status?uid={uid}&payment_status={status}&grievance_number={number}`

## Database Models

### Grievance Model Changes
```python
class Grievance(models.Model):
    grievance_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    is_payment_completed = models.BooleanField(default=False)
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)
    # ... other fields
```

**Key Points:**
- `grievance_number` is now nullable (generated only after payment)
- Auto-generated in `save()` method when `is_payment_completed=True`
- Format: `GRV{sequence:06d}` (e.g., GRV000001, GRV000002)

### GrievancePayment Model
```python
class GrievancePayment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('ABORTED', 'Aborted'),
    ]
    
    grievance = models.ForeignKey(Grievance, on_delete=models.CASCADE, related_name='payments')
    order_id = models.CharField(max_length=100, unique=True)
    tracking_id = models.CharField(max_length=100, null=True, blank=True)
    bank_ref_no = models.CharField(max_length=100, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_mode = models.CharField(max_length=50, null=True, blank=True)
    card_name = models.CharField(max_length=50, null=True, blank=True)
    raw_response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

## API Endpoints

### Create Grievance Draft
`POST /api/grievances/`
- Creates grievance without payment
- Returns grievance UID
- No grievance_number assigned yet

### Initiate Payment
`POST /api/grievances/{grievance_uid}/initiate-payment/`
- Requires authentication
- User must own the grievance
- Returns encrypted payment data

### Payment Response (Webhook)
`POST /api/grievances/payment-response/`
- No authentication required (webhook from CC Avenue)
- Handles payment success/failure
- Redirects to frontend with status

### List/View Grievances
`GET /api/grievances/`
- Students can see all their grievances (including unpaid drafts)
- College/University staff see only paid grievances with grievance_number

## Environment Variables Required

```env
CCAVENUE_MERCHANT_ID=your_merchant_id
CCAVENUE_ACCESS_CODE=your_access_code
CCAVENUE_WORKING_KEY=your_working_key
CCAVENUE_URL=https://test.ccavenue.com/transaction/transaction.do?command=initiateTransaction
CCAVENUE_REDIRECT_URL=http://your-backend-url/api/grievances/payment-response/
FRONTEND_URL=http://localhost:3000
```

## Frontend Integration

### Step 1: Create Grievance
```javascript
const response = await fetch('/api/grievances/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    category_uid: categoryUid,
    college_uid: collegeUid,
    subject: "My Issue",
    description: "Detailed description",
    contact_person_name: "John Doe",
    contact_person_phone_number: "9876543210",
    attachment_uids: [] // optional
  })
});

const { grievance } = await response.json();
const grievanceUid = grievance.uid;
```

### Step 2: Initiate Payment
```javascript
const paymentResponse = await fetch(`/api/grievances/${grievanceUid}/initiate-payment/`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const { order_id, enc_request, access_code, production_url } = await paymentResponse.json();
```

### Step 3: Submit to CC Avenue
```javascript
// Create form and submit to CC Avenue
const form = document.createElement('form');
form.method = 'POST';
form.action = production_url;

const encInput = document.createElement('input');
encInput.type = 'hidden';
encInput.name = 'encRequest';
encInput.value = enc_request;

const accessInput = document.createElement('input');
accessInput.type = 'hidden';
accessInput.name = 'access_code';
accessInput.value = access_code;

form.appendChild(encInput);
form.appendChild(accessInput);
document.body.appendChild(form);
form.submit();
```

### Step 4: Handle Payment Status
```javascript
// On payment status page
const urlParams = new URLSearchParams(window.location.search);
const uid = urlParams.get('uid');
const paymentStatus = urlParams.get('payment_status');
const grievanceNumber = urlParams.get('grievance_number');

if (paymentStatus === 'success') {
  // Show success message with grievance_number
  console.log(`Grievance ${grievanceNumber} created successfully!`);
} else {
  // Show failure message, allow retry
  console.log('Payment failed. Please try again.');
}
```

## Admin Panel

### Grievance Admin
- Shows `is_payment_completed` status in list view
- Payment information section in detail view
- Can view related payments

### GrievancePayment Admin
- Color-coded payment status badges
- Search by order_id, tracking_id, grievance_number
- Filter by payment status and date
- View raw CC Avenue response

## Migration

Run the following command to create the database migration:

```bash
python manage.py makemigrations grievance
python manage.py migrate
```

This will:
1. Add `is_payment_completed` and `payment_amount` fields to Grievance model
2. Make `grievance_number` nullable
3. Create GrievancePayment model
4. Create necessary indexes

## Testing

### Test Payment Flow
1. Create a grievance draft via API
2. Note the grievance UID
3. Initiate payment with the UID
4. Use CC Avenue test credentials
5. Complete payment on test gateway
6. Verify grievance_number is generated
7. Check payment record in admin panel

### Test Cases
- ✅ Create grievance without payment
- ✅ Initiate payment for unpaid grievance
- ✅ Prevent duplicate payment for same grievance
- ✅ Generate grievance_number on successful payment
- ✅ Handle payment failure gracefully
- ✅ Handle payment abortion
- ✅ Redirect to frontend with correct parameters

## Security Considerations

1. **Payment Verification:** Always verify payment status from CC Avenue response
2. **User Authorization:** Only grievance owner can initiate payment
3. **Idempotency:** Prevent duplicate payments for same grievance
4. **Encryption:** All payment data encrypted using CC Avenue working key
5. **Logging:** Comprehensive logging for payment transactions

## Troubleshooting

### Grievance Number Not Generated
- Check `is_payment_completed` is True
- Verify payment status is SUCCESS
- Check model's save() method is called
- Review logs for errors

### Payment Response Not Received
- Verify CCAVENUE_REDIRECT_URL is correct
- Check CC Avenue merchant configuration
- Ensure webhook endpoint is accessible
- Review CC Avenue dashboard for transaction status

### Duplicate Order IDs
- Each payment attempt creates new order_id
- Format: `GRV_{12_char_hex_uppercase}`
- Unique constraint on order_id field

## Notes

- Fixed payment amount: ₹100.00 (configurable via `payment_amount` field)
- Grievance number format: GRV000001, GRV000002, etc.
- Sequential numbering across all grievances
- Students can have multiple unpaid draft grievances
- Only paid grievances are visible to college/university staff
- Payment records are never deleted (audit trail)
