import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { GroupPreOrderService } from './group-pre-order.service';
import { API_BASE_URL } from '@app/shared/config/api-base-url.token';
import { AuthenticationService } from '@app/auth/services/authentication.service';

describe('GroupPreOrderService', () => {
  let service: GroupPreOrderService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: API_BASE_URL, useValue: 'https://test.api' },
        { provide: AuthenticationService, useValue: { getToken: () => 'id-token' } },
      ],
    });
    service = TestBed.inject(GroupPreOrderService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('requests group sessions with the owner token attached', () => {
    service.getSessions$('group-1').subscribe((res) => expect(res.total).toBe(10));

    const req = httpMock.expectOne('https://test.api/guest/groups/group-1/sessions');
    expect(req.request.method).toBe('GET');
    expect(req.request.headers.get('Authorization')).toBe('Bearer id-token');
    req.flush({ participants: [], total: 10 });
  });

  it('posts the reservation id when submitting the group pre-order', () => {
    service.submit$('group-1', 'res-1').subscribe((items) => expect(items.length).toBe(1));

    const req = httpMock.expectOne('https://test.api/group-reservations/group-1/submit');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ reservationId: 'res-1' });
    req.flush([{ dishId: 'dish-1', quantity: 2 }]);
  });

  it('propagates server errors to the caller', () => {
    let status = 0;
    service.submit$('group-1', 'res-1').subscribe({ error: (err) => (status = err.status) });

    httpMock
      .expectOne('https://test.api/group-reservations/group-1/submit')
      .flush({ message: 'No submitted sessions' }, { status: 400, statusText: 'Bad Request' });
    expect(status).toBe(400);
  });
});
