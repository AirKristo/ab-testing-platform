/**
 * Cart context — global state for the shopping cart.
 */
import { createContext, useContext, useState, useCallback } from 'react';
import api from '../api/client';

const CartContext = createContext();

// Hardcoded user ID for demo purposes
export const DEMO_USER_ID = 1;

export function CartProvider({ children }) {
  const [cart, setCart] = useState({ items: [], cart_total: 0, item_count: 0 });
  const [loading, setLoading] = useState(false);

  const fetchCart = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get(`/cart/${DEMO_USER_ID}`);
      setCart(response.data);
    } catch (error) {
      console.error('Failed to fetch cart:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const addToCart = useCallback(async (productId, quantity = 1) => {
    try {
      setLoading(true);
      const response = await api.post('/cart/add', {
        user_id: DEMO_USER_ID,
        product_id: productId,
        quantity,
      });
      setCart(response.data);
      return true;
    } catch (error) {
      console.error('Failed to add to cart:', error);
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateQuantity = useCallback(async (cartItemId, quantity) => {
    try {
      setLoading(true);
      const response = await api.put(`/cart/item/${cartItemId}`, { quantity });
      setCart(response.data);
    } catch (error) {
      console.error('Failed to update cart:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const removeItem = useCallback(async (cartItemId) => {
    try {
      setLoading(true);
      const response = await api.delete(`/cart/item/${cartItemId}`);
      setCart(response.data);
    } catch (error) {
      console.error('Failed to remove item:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const checkout = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.post('/orders/checkout', {
        user_id: DEMO_USER_ID,
      });
      // Clear local cart state after successful checkout
      setCart({ items: [], cart_total: 0, item_count: 0 });
      return response.data;
    } catch (error) {
      console.error('Failed to checkout:', error);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <CartContext.Provider value={{
      cart,
      loading,
      fetchCart,
      addToCart,
      updateQuantity,
      removeItem,
      checkout,
    }}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
}