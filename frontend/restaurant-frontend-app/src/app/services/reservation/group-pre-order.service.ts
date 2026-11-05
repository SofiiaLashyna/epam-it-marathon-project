import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { GroupPreOrderItem, GroupSessions } from '@app/models/reservations/group-pre-order.model';
import { API_BASE_URL } from '@app/shared/config/api-base-url.token';
import { AuthenticationService } from '@app/auth/services/authentication.service';

@Injectable({
  providedIn: 'root',
})
export class GroupPreOrderService {
  private readonly baseUrl = inject(API_BASE_URL);
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthenticationService);

  // The token interceptor deliberately skips every '/guest/' URL (guest-session flow),
  // but this endpoint is for the reservation owner, so the Cognito token is attached here.
  getSessions$(groupReservationId: string): Observable<GroupSessions> {
    const idToken = this.authService.getToken();
    const headers = idToken ? new HttpHeaders({ Authorization: `Bearer ${idToken}` }) : undefined;
    return this.http.get<GroupSessions>(
      `${this.baseUrl}/guest/groups/${encodeURIComponent(groupReservationId)}/sessions`,
      { headers },
    );
  }

  submit$(groupReservationId: string, reservationId: string): Observable<GroupPreOrderItem[]> {
    return this.http.post<GroupPreOrderItem[]>(
      `${this.baseUrl}/group-reservations/${encodeURIComponent(groupReservationId)}/submit`,
      { reservationId },
    );
  }
}
