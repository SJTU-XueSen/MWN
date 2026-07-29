export type StudentActivity = {
  id: string;
  title: string;
  description: string;
  date: string;
  location: string;
  organizer: string;
  contact: string;
  createdAt: string;
};

export type StudentActivityCreate = {
  title: string;
  description: string;
  date: string;
  location: string;
  organizer: string;
  contact: string;
};
