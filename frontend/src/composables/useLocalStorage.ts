import { ref, watch, type Ref } from 'vue';

export function useLocalStorage<T>(key: string, defaultValue: T): [Ref<T>, (value: T) => void, () => void] {
  const storedValue = localStorage.getItem(key);
  const value = ref(storedValue ? (JSON.parse(storedValue) as T) : defaultValue) as Ref<T>;

  watch(
    value,
    (newValue) => {
      localStorage.setItem(key, JSON.stringify(newValue));
    },
    { deep: true },
  );

  const setValue = (newValue: T) => {
    value.value = newValue;
  };

  const removeValue = () => {
    localStorage.removeItem(key);
    value.value = defaultValue;
  };

  return [value, setValue, removeValue];
}
