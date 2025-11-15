export const addCookie = (key: string, value: string, durationHours: number) => {
  const date = new Date();
  date.setTime(date.getTime() + durationHours * 60 * 60 * 1000);
  document.cookie = `${key}=${value}; expires=${date.toUTCString()};`;
};

export const getCookie = (key: string) => {
  const cookieStrings = decodeURIComponent(document.cookie).split(";");
  let value: null | string = null;
  cookieStrings.forEach((element) => {
    if (element.indexOf(key) == 0) {
      value = element.substring(key.length + 1);
      return;
    }
  });
  return value;
};
