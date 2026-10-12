export interface User {
  id: string;
  username: string;
  email: string;
  fullname?: string | null;
  role?: string;
  avatar?: string;
  firstName?: string;
  lastName?: string;
  phone?: string;
  createdAt?: string;
  updatedAt?: string;
}
