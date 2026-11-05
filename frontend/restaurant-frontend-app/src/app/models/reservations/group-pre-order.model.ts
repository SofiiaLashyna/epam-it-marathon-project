export interface GroupParticipantItem {
  dish: {
    id: string;
    name: string;
    price: number;
    imageUrl?: string | null;
  };
  quantity: number;
}

export interface GroupParticipant {
  id: string | null;
  type: 'Owner' | 'Guest';
  name: string;
  items: GroupParticipantItem[];
  total: number;
  isSubmitted: boolean;
}

export interface GroupSessions {
  participants: GroupParticipant[];
  total: number;
}

export interface GroupPreOrderItem {
  dishId: string;
  quantity: number;
}
