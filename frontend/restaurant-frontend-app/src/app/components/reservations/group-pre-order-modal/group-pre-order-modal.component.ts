import { CurrencyPipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  input,
  OnInit,
  output,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { switchMap } from 'rxjs';
import { ReservationCustomer } from '@app/models/reservations/reservation.model';
import { GroupParticipant } from '@app/models/reservations/group-pre-order.model';
import { GuestInviteService } from '@app/services/reservation/guest-invite.service';
import { GroupPreOrderService } from '@app/services/reservation/group-pre-order.service';
import { ToastService } from '@app/services/toast/toast.service';
import { ModalComponent } from '@app/shared/custom-components/modal/modal.component';

type LoadState = 'loading' | 'ready' | 'error';

@Component({
  selector: 'app-group-pre-order-modal',
  imports: [CurrencyPipe, ModalComponent],
  templateUrl: './group-pre-order-modal.component.html',
  styleUrl: './group-pre-order-modal.component.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class GroupPreOrderModalComponent implements OnInit {
  private readonly guestInviteService = inject(GuestInviteService);
  private readonly groupPreOrderService = inject(GroupPreOrderService);
  private readonly toastService = inject(ToastService);
  private readonly destroyRef = inject(DestroyRef);

  readonly reservation = input.required<ReservationCustomer>();
  readonly closed = output<void>();

  readonly state = signal<LoadState>('loading');
  readonly participants = signal<GroupParticipant[]>([]);
  readonly total = signal(0);
  readonly submitting = signal(false);
  readonly submittedGroup = signal(false);

  private readonly groupReservationId = signal<string | null>(null);
  private readonly inviteToken = signal<string | null>(null);

  readonly inviteLink = computed(() => {
    const token = this.inviteToken();
    return token ? `${window.location.origin}/join/${token}` : '';
  });

  readonly guests = computed(() => this.participants().filter((person) => person.type === 'Guest'));
  readonly readyCount = computed(() => this.guests().filter((person) => person.isSubmitted).length);
  readonly readyTotal = computed(() =>
    this.participants()
      .filter((person) => person.isSubmitted)
      .reduce((sum, person) => sum + person.total, 0),
  );
  readonly canSubmit = computed(
    () => !this.submitting() && !this.submittedGroup() && this.readyTotal() > 0,
  );

  ngOnInit(): void {
    this.guestInviteService
      .getInviteToken$(this.reservation().id)
      .pipe(
        switchMap(({ token }) => {
          this.inviteToken.set(token);
          return this.guestInviteService.getInvite$(token);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (invite) => {
          this.groupReservationId.set(invite.GroupReservationId);
          this.refresh();
        },
        error: () => this.state.set('error'),
      });
  }

  refresh(): void {
    const groupId = this.groupReservationId();
    if (!groupId) {
      return;
    }

    this.state.set('loading');
    this.groupPreOrderService
      .getSessions$(groupId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (sessions) => {
          this.participants.set(sessions.participants);
          this.total.set(sessions.total);
          this.state.set('ready');
        },
        error: () => this.state.set('error'),
      });
  }

  submit(): void {
    const groupId = this.groupReservationId();
    if (!groupId || !this.canSubmit()) {
      return;
    }

    this.submitting.set(true);
    this.groupPreOrderService
      .submit$(groupId, this.reservation().id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (items) => {
          const dishCount = items.reduce((sum, item) => sum + item.quantity, 0);
          this.submitting.set(false);
          this.submittedGroup.set(true);
          this.toastService.success(
            `${dishCount} ${dishCount === 1 ? 'dish was' : 'dishes were'} added to your pre-order.`,
            'Group pre-order confirmed!',
          );
        },
        error: () => this.submitting.set(false),
      });
  }

  async copyLink(): Promise<void> {
    const link = this.inviteLink();
    if (!link) {
      return;
    }
    try {
      await navigator.clipboard.writeText(link);
      this.toastService.success('Share it with your friends.', 'Link copied!');
    } catch {
      this.toastService.error('Could not copy the link. Please copy it manually.');
    }
  }

  onClose(): void {
    this.closed.emit();
  }
}
