export type MemoItem = {
  id: string;
  title: string;
  note: string;
  deadline: string;
  createdAt: string;
};

export type MemoCreateRequest = {
  title: string;
  note: string;
  deadline: string;
};
