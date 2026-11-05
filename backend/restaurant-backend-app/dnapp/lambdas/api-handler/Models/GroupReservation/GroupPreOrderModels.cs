namespace APIHandler.Models.GroupReservation;

public record SubmitGroupPreOrderRequest(string? ReservationId);

public record GroupPreOrderItem(string DishId, int Quantity);

public record OwnerGuestSessionIdResponse(string GuestSessionId);
